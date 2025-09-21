import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import requests
from os import path
from datetime import *
from typing import Optional

import chromedriver_autoinstaller

CARD_TYPE_SEPARATORS = ["Creature", "Land", "Instant", "Sorcery", "Artifact", "Enchantment", "Planeswalker",
                                    "Tribal", "Typal", "Cards", "Other", "Rarity"]


chromedriver_autoinstaller.install()
chromeOptions = Options()
chromeOptions.add_argument("--headless")
chromeOptions.add_argument("--log-level=3")

try:
    driver = webdriver.Chrome(options=chromeOptions)
except selenium.common.exceptions.SessionNotCreatedException as e:
    print("Issue with ChromeDriver, cannot create Selenium Session")
    raise e

def updateCardPropertiesDataset(format: str) -> None:
    """
    Calls the Scryfall API to update the local list of all card names and CMCs
    """

    if format == None:
        format = "vintage"
    else:
        format = format.lower()

    # get link to most recent bulk data file from Scryfall
    re = requests.get("https://scryfall.com/docs/api/bulk-data")
    bulkDatasetLink = re.text.split("Oracle Cards")[1]
    bulkDatasetLink = bulkDatasetLink.split('href="')[1].split('">')[0]

    # call api for that file
    re = requests.get(bulkDatasetLink)

    out = {}
    for c in re.json():
        if c['legalities'][format] in ['legal', 'banned']:
            try:
                out[c['name']] = {'mana': c['mana'], 'cmc': int(c['cmc']), 'url': c['scryfall_uri'],
                                  'oracle': c['oracle_text'], 'type': c['type_line']}
            except KeyError:
                # Encountered a flip card
                out[c['name']] = {'mana': 'None', 'cmc': 0, 'url': c['scryfall_uri'], 'oracle': 'flip card',
                                  'type': 'flip card'}

    with open("Data/card_properties.json", "w") as f:
        json.dump(out, f)

    DFCs = {}  # Cards with 2 names separated by " // " DFCs, split, fuse, etc. {first half: full name}
    for k in out.keys():
        if " // " in k and k.split(" // ")[0] != k.split(" // ")[1]:
            DFCs[k.split(" // ")[0]] = k
    with open("Data/double_cards.json", "w") as f:
        json.dump(DFCs, f)
    print("successfully updated card properties dataset from Scryfall")


def scrapeUrls(datasetFile: str, urls: list[str]) -> None:
    """
    Scrapes all given urls from www.mtgo.com/decklists/... to extract deck information
    writes to the output_file information in json format: payer name, url of event, event date, maindeck, sideboard
    Adds all urls successfully scraped to Data/scraped_urls_NAMEOFOUTPUTFILE.txt
    """

    if not urls:
        return

    # Get dict of DFCs and split cards, so they can be made consistent with Scryfall formatting later
    with open("Data/double_cards.json", "r") as f:
        DFCs = json.load(f)  # formatted like: {first/front card: full card name}

    scrapedUrls = []
    erroredUrls = []
    output = []
    for url in urls:
        urlEnding = url.replace("https://www.mtgo.com/decklist/", "")
        print(f"Gathering {len(urls)} decks from: ", url)
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'decklist')))
            content = driver.find_elements(By.CLASS_NAME, 'decklist')
            scrapedUrls.append(urlEnding)
        except selenium.common.exceptions.TimeoutException:
            erroredUrls.append(urlEnding)
            continue

        for decklist in content:
            deckContents = decklist.text
            deckContents = deckContents.split("\n")
            deckDate = urlEnding.split("-")
            year = int(deckDate[-3])
            month = int(deckDate[-2])
            day = int(deckDate[-1][:2])
            deckDate = date(year, month, day)
            player = deckContents[0]
            player = player.split(" ")[0]
            deck = {"player": player, "url": urlEnding, 'date': deckDate, "main": {}, "side": {}}
            
            md = True
            for i in range(9, len(deckContents)):
                if "Sideboard" in deckContents[i]:
                    md = False
                    continue
                for t in CARD_TYPE_SEPARATORS:
                    if t in deckContents[i]:
                        break
                else:
                    # Check if the card is a split card/DFC
                    quantity = deckContents[i].split(" ", 1)[0]
                    card = deckContents[i].split(" ", 1)[1]

                    # Fix non-English character issues
                    # Note: edge cases with non-English characters are currently being investigated as some behave oddly
                    unicodeReplacements = {"Ã\x86": "Ae", "\u00c3\u00b3": "\u00f3"}
                    for k in unicodeReplacements.keys():
                        if k in card:
                            card.replace(k, unicodeReplacements[k])

                    if "/" in card:
                        card = card.split("/")[0]
                    for double in DFCs.keys():
                        if double == card:
                            card = DFCs[double]
                            break

                    if md:
                        deck["main"][card.lower()] = int(quantity)
                    else:
                        deck["side"][card.lower()] = int(quantity)
            output.append(deck)

    if path.isfile(datasetFile):
        with open(datasetFile, "r") as f:
            existingContent = json.load(f)
            output = existingContent + output
    with open(datasetFile, "w") as f:
        json.dump(output, f, default=str)

    urlFileName = "Data/scraped_urls_" + datasetFile.split("/")[-1].split(".")[0] + ".txt"
    with open(urlFileName, "a") as f:
        urlStr = "\n" + "\n".join(scrapedUrls)
        f.write(urlStr)

    if len(erroredUrls) == 0:
        return

    print("\nURLS That weren't reached and should be run again:")
    for url in erroredUrls:
        print(url)
    print()


def getNewUrls(datasetFile: str, format: str, date: str = "") -> list[str]:
    """
    Gets each event url from a page with all events from a month that has not yet been scraped
    The date should have the format "yyyy/mm"
    """
    url = f"https://www.mtgo.com/decklists/{date}?filter={format.title()}"
    foundUrls = []
    newUrls = []

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, format)))
    except selenium.common.exceptions.TimeoutException:
        print(f"Unable to find urls from {url}. Try again")
        return []
    
    content = driver.find_elements(By.PARTIAL_LINK_TEXT, format)
    for l in content:
        foundUrls.append(l.get_attribute("href"))

    # Skip urls that have already been scraped
    try:
        urlFileName = "Data/scraped_urls_" + datasetFile.split("/")[-1].split(".")[0] + ".txt"
        with open(urlFileName, "r") as f:
            previouslySeenUrls = f.read()
    except FileNotFoundError:
        previouslySeenUrls = ""

    for url in foundUrls:
        urlEnding = url.replace("https://www.mtgo.com/decklist/", "")
        if urlEnding not in previouslySeenUrls:
            newUrls.append(url)
    return newUrls[::-1]  # reverse order to preserve chronology

def getUrlsForMonths(datasetFile: str, format: str, skip: bool, grace: Optional[int] = 7, startDate: Optional[str] = None, endDate: Optional[str] = None) -> None:
    """
    Scrape one or more months of data for one format, and add data to datasetFile
    date inputs should be like 'yyyy/mm'
    """

    if not skip:
        updateCardPropertiesDataset(format)

    format = format.capitalize()

    dates = []

    if startDate == None:
        # scrape the previous [grace] days to prevent coverage issues with automated usage
        startDate = (datetime.today() - timedelta(days=grace)).strftime("%Y/%m")

    if endDate == None:
        endDate = datetime.today().strftime("%Y/%m")

    start = startDate.split("/")
    end = endDate.split("/")
    
    start = [int(v) for v in start]
    end =   [int(v) for v in end]

    for year in range(start[0], end[0] + 1):
        yearStartMonth = 1
        yearEndMonth = 12

        if year == start[0]:
            yearStartMonth = start[1]
        if year == end[0]:
            yearEndMonth = end[1]
        
        for month in range(yearStartMonth, yearEndMonth + 1):
            dates.append(f"{year}/{month:02}")

    for date in dates:
        scrapeUrls(datasetFile, getNewUrls(datasetFile, format, date))
