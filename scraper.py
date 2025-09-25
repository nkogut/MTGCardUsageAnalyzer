import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import orjson as json
import requests
from os import path
from datetime import *
from typing import Optional

import chromedriver_autoinstaller

CARD_TYPE_SEPARATORS = ["Creature", "Land", "Instant", "Sorcery", "Artifact", "Enchantment", "Planeswalker", "Battle"
                        "Tribal", "Typal", "Cards", "Other", "Rarity"]

chromedriver_autoinstaller.install()
chromeOptions = Options()
chromeOptions.add_argument("--headless")
chromeOptions.add_argument("--log-level=3")
chromeOptions.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2,}) # Prevent images from loading

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
    print("successfully updated card properties dataset from Scryfall\n")


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
        DFCs = json.loads(f.read())  # formatted like: {first/front card: full card name}

    datasetName = datasetFile.split("/")[-1].split(".")[0]
    urlFileName = f"Data/{datasetName}_urls.json"
    scrapedUrls = []
    erroredUrls = []
    decks = []
    numDecks = 0

    date_ = dateFromUrl(urls[0])
    print(f"Scraping {len(urls)} events for {date_.month}/{date_.year}")
    for url in urls:
        urlEnding = url.replace("https://www.mtgo.com/decklist/", "")
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'decklist')))
            content = driver.find_elements(By.CLASS_NAME, 'decklist')
            print(f"Gathering {len(content)} decks from", url)
            scrapedUrls.append(urlEnding)
        except selenium.common.exceptions.TimeoutException:
            erroredUrls.append(urlEnding)
            continue

        for decklist in content:
            deckContents = decklist.text
            deckContents = deckContents.split("\n")
            deckDate = dateFromUrl(urlEnding)
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
            numDecks += 1
            decks.append(deck)

    createDatasetFileIfNotExist(datasetFile)
    with open(datasetFile, "r") as f:
        storedDecks = json.loads(f.read()) 
        storedDecks += decks

    with open(datasetFile, "w") as f:
        print(f"Saving {numDecks} decklists to {datasetFile} for {date_.month}/{date_.year}")
        json.dump(storedDecks, f, default=str)

    createUrlFileIfNotExist(urlFileName)
    with open(urlFileName, "r") as f:
        storedUrls = json.loads(f.read())
        storedUrls["completed"] += scrapedUrls
        storedUrls["failed"]["event"] = [url for url in storedUrls["failed"]["event"] if url not in scrapedUrls]
        storedUrls["failed"]["event"] = list(set(erroredUrls + storedUrls["failed"]["event"]))

    if len(erroredUrls) > 0:
        print(f"\nError: {len(erroredUrls)} Url(s) failed. Please try them again with 'python scrape.py <dataset> <format> -retry\n")

    with open(urlFileName, "w") as f:
        json.dump(storedUrls, f)


def dateFromUrl(url: str) -> date:
    deckDate = url.split("-")
    year = int(deckDate[-3])
    month = int(deckDate[-2])
    day = int(deckDate[-1][:2])
    return date(year, month, day)


def getNewUrls(datasetFile: str, format: str, date: str) -> list[str]:
    """
    Gets each event url from a page with all events from a month that has not yet been scraped
    The date should have the format "yyyy/mm"
    """
    listingUrl = f"https://www.mtgo.com/decklists/{date}?filter={format.title()}"
    datasetName = datasetFile.split("/")[-1].split(".")[0]
    urlFileName = f"Data/{datasetName}_urls.json"
    foundUrls = []
    newUrls = []

    try:
        driver.get(listingUrl)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, format)))
    except selenium.common.exceptions.TimeoutException:
        print(f"Error: Unable to find urls from {listingUrl}. Please try them again with 'python scrape.py <dataset> <format> -err'\n")
        
        createUrlFileIfNotExist(urlFileName)
        with open(urlFileName, "r") as f:
            storedUrls = json.loads(f.read())
            storedUrls["failed"]["listing"] = list(set([date] + storedUrls["failed"]["listing"]))
            
        with open(urlFileName, "w") as f:
            json.dump(storedUrls, f)
        return []
    
    content = driver.find_elements(By.PARTIAL_LINK_TEXT, format)
    for l in content:
        foundUrls.append(l.get_attribute("href"))

    createUrlFileIfNotExist(urlFileName)
    with open(urlFileName, "r") as f:
        storedUrls = json.loads(f.read())

        for url in foundUrls:
            urlEnding = url.replace("https://www.mtgo.com/decklist/", "")
            if urlEnding not in storedUrls["completed"]:
                newUrls.append(url)

        if listingUrl in storedUrls["failed"]["listing"]:
            storedUrls["failed"]["listing"].remove(listingUrl)

    with open(urlFileName, "w") as f:
            json.dump(storedUrls, f)

    return newUrls


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

def retryErroredUrls(dsPath: str, format: str):
    urlPath = dsPath.replace(".json", "_urls.json")
    with open(urlPath, "r") as f:
        urls = json.loads(f.read())
    fullUrls = ["https://www.mtgo.com/decklist/" + urlEnding for urlEnding in urls["failed"]["event"]]
    
    numFailedEvents = len(urls["failed"]["event"])
    numFailedListings = len(urls["failed"]["listing"])

    scrapeUrls(dsPath, fullUrls)
    
    for date in urls["failed"]["listing"]:
        scrapeUrls(dsPath, getNewUrls(dsPath, format, date))

    # Get updated urls after retries have occurred
    with open(urlPath, "r") as f:
        urls = json.loads(f.read())

    newNumEvents = len(urls["failed"]["event"])
    newNumListings = len(urls["failed"]["listing"])

    print(f"Number of urls retried:")
    print(f"Events: {numFailedEvents}")
    print(f"Months: {numFailedListings}")
    print()
    print(f"Number of urls that need to be retried again:")
    print(f"Events: {newNumEvents}")
    print(f"Months: {newNumListings}")


def createFileIfNotExist(filePath: str, content: any) -> None:
    if not path.isfile(filePath):
        with open(filePath, "w+") as f:
            json.dump(content, f)

def createDatasetFileIfNotExist(datasetFile: str) -> None:
    createFileIfNotExist(datasetFile, [])

def createUrlFileIfNotExist(urlFile: str) -> None:
    createFileIfNotExist(urlFile, {"completed": [], "failed": {"listing": [], "event": []}})
