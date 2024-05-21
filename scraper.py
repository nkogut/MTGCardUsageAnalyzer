import selenium.common.exceptions
from selenium import webdriver  # basic selenium
from selenium.webdriver.common.by import By  # wait
from selenium.webdriver.support.ui import WebDriverWait  # wait
from selenium.webdriver.support import expected_conditions as EC  # wait
from selenium.webdriver.chrome.options import Options  # headless
import json
import requests # For the scryfall API
from os import path
from datetime import *

import chromedriver_autoinstaller

OUTPUT_FILE = "Data/full_modern.json"

chromedriver_autoinstaller.install()
chrome_options = Options()
chrome_options.add_argument("--headless")

try:
    driver = webdriver.Chrome(options=chrome_options)
except selenium.common.exceptions.SessionNotCreatedException as e:
    print("Issue with ChromeDriver, cannot create Selenium Session")
    raise e

# Get dict of DFCs and split cards, so they can be made consistent with scryfall formatting later
with open("Data/double_cards.json", "r") as f:
    double_cards = json.load(f)  # {first/front card: full card name}

def update_card_properties():
    # get link to most recent bulk data file from Scryfall
    re = requests.get("https://scryfall.com/docs/api/bulk-data")
    temp_page_loc = re.text.split("Oracle Cards")[1]
    bulk_data_file = temp_page_loc.split('href="')[1].split('">')[0]

    # call api for that file
    re = requests.get(bulk_data_file)

    out = {}
    for c in re.json():
        if c['legalities']['modern'] in ['legal', 'banned']:
            try:
                out[c['name']] = {'mana_cost': c['mana_cost'], 'cmc': int(c['cmc']), 'url': c['scryfall_uri'],
                                  'oracle': c['oracle_text'], 'type': c['type_line']}
            except KeyError:
                out[c['name']] = {'mana_cost': 'None', 'cmc': 0, 'url': c['scryfall_uri'], 'oracle': 'flip card',
                                  'type': 'flip card'}

    with open("Data/card_properties.json", "w") as f:
        json.dump(out, f)

    double_cards = {}  # Cards with 2 names separated by " // " DFCs, split, fuse, etc. {first half: full name}
    for k in out.keys():
        if " // " in k and k.split(" // ")[0] != k.split(" // ")[1]:
            double_cards[k.split(" // ")[0]] = k
    with open("Data/double_cards.json", "w") as f:
        json.dump(double_cards, f)
    print("successfully updated card properties dataset from Scryfall")


def scrape_urls(urls):
    """
    urls: list of urls to be scraped - get using find_new_urls()

    writes to the output_file information in json format: payer name, url of event, event date, maindeck, sideboard
    returns nothing
    """

    if not urls:
        return

    errored_urls = []

    for url in urls:
        print("Gathering decks from:", url)
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'decklist')))
            content = driver.find_elements(By.CLASS_NAME, 'decklist')
        except selenium.common.exceptions.TimeoutException:
            errored_urls.append(url)
            continue

        output = []
        for decklist in content:
            d = decklist.text
            d = d.split("\n")
            deck_date = url.split("-")
            deck_date = date(int(deck_date[-3]), int(deck_date[-2]), int(deck_date[-1][:2]))
            player = d[0]
            deck = {"player": player, "url": url, 'date': deck_date, "maindeck": {}, "sideboard": {}}
            card_type_separators = ["Creature", "Land", "Instant", "Sorcery", "Artifact", "Enchantment", "Planeswalker", "Tribal", "Cards", "Other", "Rarity"]

            md = True
            for i in range(9, len(d)):
                if "Sideboard" in d[i]:
                    md = False
                    continue
                for t in card_type_separators:
                    if t in d[i]:
                        break
                else:
                    quantity = d[i].split(" ", 1)[0]
                    card = d[i].split(" ", 1)[1]
                    # Check if the card is a split card/DFC

                    # Fix character issues that show up in weird langauges
                    unicode_issues = {"Ã\x86": "Ae", "\u00c3\u00b3": "\u00f3"}
                    # can this be fixed with r'str' or something?
                    for k in unicode_issues.keys():
                        if k in card:
                            card.replace(k, unicode_issues[k])

                    # card = card.replace("Ã\x86", "Ae")  # AE symbol gets messed up - looks like "\u00c3\u0086" in output
                    if "/" in card:
                        card = card.split("/")[0]
                    for double in double_cards.keys():
                        if double == card:
                            card = double_cards[double]
                            break

                    if md:
                        deck["maindeck"][card] = int(quantity)
                    else:
                        deck["sideboard"][card] = int(quantity)
            output.append(deck)

        if not path.isfile(OUTPUT_FILE):
            content = output # The only content will be what was just scraped
        else:
            with open(OUTPUT_FILE, "r") as f:
                content = json.load(f)
                for deck_dict in output:
                    content.append(deck_dict)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(content, f, default=str)

        with open("Data/scraped_urls.txt", "a") as f:
            f.write("\n" + url)

    if len(errored_urls) == 0:
        return

    print("URLS That through errors and need to be run again:")
    for url in errored_urls:
        print(url)
    print("End of errors")

def find_new_urls(url="https://www.mtgo.com/decklists/?filter=Modern"):
    """
    input url: "https://www.mtgo.com/decklists/yyyy/mm?filter=Modern"" - date optional - note: changed by Daybreak 12/2023
    return urls for all events in month that have not already been scraped
    """
    found_urls = []
    confirmed_new_urls = []

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, 'Modern')))
    except selenium.common.exceptions.TimeoutException:
        print(f"Unable to find urls from {url}. Try again")
        return []
    content = driver.find_elements(By.PARTIAL_LINK_TEXT, 'Modern')
    for l in content:
        found_urls.append(l.get_attribute("href"))

    # Check new scraped urls against previously scraped urls
    with open("Data/scraped_urls.txt", "r") as f:
        previously_scraped_urls = f.read()
        for url in found_urls:
            if url not in previously_scraped_urls:
                confirmed_new_urls.append(url)
    return confirmed_new_urls[::-1]  #reverse order to preserve chronology - no functional purpose

def scrape_historical_urls(dates):
    """
    For going through multiple urls in a  list at once
    input should be list like ['yyyy/mm', 'yyyy/mm']
    """
    for date in dates:
        scrape_urls(urls=find_new_urls(f"https://www.mtgo.com/decklists/{date}?filter=Modern"))

# scrape_urls(find_new_urls())
