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
from unidecode import unidecode
import utils

import chromedriver_autoinstaller

CARD_TYPE_SEPARATORS = ["Creature (", "Land (", "Instant (", "Sorcery (", "Artifact (", "Enchantment (", "Planeswalker (",
                        "Other (", "Rarity", "Cards"]
''' 
Notes on other types: 
Battles are "Other ("
Tribal / Kindred are no longer used (they just use the other type)
"Cards" follows the quantity of maindeck cards and doses not have a "(". No legal cards have a name that conflicts with this weaker separator
'''

DRIVER_TIMEOUT = 8

chromedriver_autoinstaller.install()
chromeOptions = Options()
chromeOptions.add_argument("--headless")
chromeOptions.add_argument("--log-level=3") # Ignore unimpactful errors
chromeOptions.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2,}) # Prevent images from loading

try:
    driver = webdriver.Chrome(options=chromeOptions)
except selenium.common.exceptions.SessionNotCreatedException as e:
    print("Error: Issue with ChromeDriver, cannot create Selenium Session")
    raise e

def updateCardPropertiesDataset() -> None: 
    """
    Calls the Scryfall API to update the local list of all card names and CMCs
    Note: This completely remakes Data/card_properties.json each time 
    as this is faster than loading the existing one to modify it
    """

    # get link to most recent bulk data file from Scryfall
    re = requests.get("https://scryfall.com/docs/api/bulk-data")
    bulkDatasetLink = re.text.split("Oracle Cards")[1]
    bulkDatasetLink = bulkDatasetLink.split('href="')[1].split('">')[0]

    # call api for that file
    re = requests.get(bulkDatasetLink)

    out = {}
    for c in re.json():
        if c["layout"] in ["vanguard", "art_series", "planar", "scheme"]:
            continue
        name = c["name"]
        lowerName = unidecode(name).lower().split(" //")[0]
        uri = c["scryfall_uri"]
        type = c["type_line"]
        
        if "mana_cost" in c:
            manaCost = c["mana_cost"]
        else:
            manaCost = "{0}"
        
        if "cmc" in c:
            cmc = c["cmc"]
        else:
            cmc = 0

        # oracle = c["oracle_text"]
        
        out[lowerName] = {"displayName": name, "type": type, "uri": uri, "manaCost": manaCost, "cmc": cmc}


    with open("Data/card_properties.json", "wb") as f:
        f.write(json.dumps(out))

    print("successfully updated card properties dataset from Scryfall\n")

def scrapeUrls(datasetFile: str, urls: list[str]) -> None:
    """
    Scrapes all given urls from www.mtgo.com/decklists/... to extract deck information
    writes to the output_file information in json format: payer name, url of event, event date, maindeck, sideboard
    Adds all urls successfully scraped to Data/scraped_urls_NAMEOFOUTPUTFILE.txt
    """

    if not urls:
        return

    datasetName = datasetFile.split("/")[-1].split(".")[0]
    urlFileName = f"Data/{datasetName}_urls.json"
    scrapedUrls = []
    erroredUrls = []
    deadUrls = []
    decks = []
    numDecks = 0

    print(f"Scraping {len(urls)} events")
    for url in urls:
        urlEnding = url.replace("https://www.mtgo.com/decklist/", "")
        try:
            driver.get(url)
            wait = WebDriverWait(driver, DRIVER_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'decklist-item-page')))
            # try:
            content = driver.find_elements(By.CLASS_NAME, 'decklist')
            if len(content) == 0:
                print(f"Error: no decks present at {url}")
                deadUrls.append(urlEnding)
                continue

            print(f"Gathering {len(content)} decks from", url)
            scrapedUrls.append(urlEnding)
            
        except selenium.common.exceptions.TimeoutException:
            if driver.current_url == "https://www.mtgo.com/decklists":
                # Page was removed
                print(f"Error: {url} was removed.")
                deadUrls.append(urlEnding)
                continue
            erroredUrls.append(urlEnding)
            print(driver.current_url)
            continue

        for decklist in content:
            deckContents = decklist.text
            deckContents = deckContents.split("\n")
            deckDate = dateFromUrl(urlEnding)
            player = deckContents[0]
            player = unidecode(player.split(" ")[0])
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
                    quantity = deckContents[i].split(" ", 1)[0]

                    card = deckContents[i].split(" ", 1)[1] 

                    card = unidecode(card) # convert all characters to English. Prevents key errors when matching with card_properties.json.
                    card = card.lower().split("/")[0] # For DFCs only use the front name

                    if md:
                        deck["main"][card] = int(quantity)
                    else:
                        deck["side"][card] = int(quantity)
            numDecks += 1
            decks.append(deck)

    createDatasetFileIfNotExist(datasetFile)
    with open(datasetFile, "r") as f:
        storedDecks = json.loads(f.read()) 
        storedDecks += decks

    with open(datasetFile, "wb") as f:
        print(f"Saving {numDecks} decklists to {datasetFile}")
        f.write(json.dumps(storedDecks))

    createUrlFileIfNotExist(urlFileName)
    with open(urlFileName, "r") as f:
        storedUrls = json.loads(f.read())
        storedUrls["completed"] += scrapedUrls
        storedUrls["failed"]["event"] = [url for url in storedUrls["failed"]["event"] if url not in scrapedUrls and url not in deadUrls]
        storedUrls["failed"]["event"] = list(set(erroredUrls + storedUrls["failed"]["event"]))
        storedUrls["failed"]["dead"] = list(set(deadUrls + storedUrls["failed"]["dead"]))

    numErrors = len(erroredUrls)
    if numErrors > 0:
        print(f"\nError: Failed to reach {numErrors} Url{'s' if (numErrors > 1) else ''}. Please try them again with 'python scrape.py <dataset> <format> -retry'\n")

    with open(urlFileName, "wb") as f:
        f.write(json.dumps(storedUrls))


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
    format = format.title()
    listingUrl = f"https://www.mtgo.com/decklists/{date}?filter={format}"
    datasetName = datasetFile.split("/")[-1].split(".")[0]
    urlFileName = f"Data/{datasetName}_urls.json"
    foundUrls = []
    newUrls = []

    createUrlFileIfNotExist(urlFileName)
    with open(urlFileName, "r") as f:
        storedUrls = json.loads(f.read())

    try:
        driver.get(listingUrl)
        wait = WebDriverWait(driver, DRIVER_TIMEOUT)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "decklists-list")))
    except selenium.common.exceptions.TimeoutException:
        print(f"Error: Unable to access {listingUrl}. Please try them again with 'python scrape.py <dataset> <format> -err'\n")
        storedUrls["failed"]["listing"] = list(set([date] + storedUrls["failed"]["listing"]))
        with open(urlFileName, "wb") as f:
            f.write(json.dumps(storedUrls))
        return []
    
    content = driver.find_elements(By.PARTIAL_LINK_TEXT, format)
    if len(content) == 0:
        print(f"Error: No {format} decklists found at {listingUrl}'")
        storedUrls["failed"]["dead"] = list(set([date] + storedUrls["failed"]["dead"]))
        if date in storedUrls["failed"]["listing"]:
            storedUrls["failed"]["listing"].remove(date)

        with open(urlFileName, "wb") as f:
            f.write(json.dumps(storedUrls))
        return []

    for l in content:
        foundUrls.append(l.get_attribute("href"))

    # createUrlFileIfNotExist(urlFileName)
    # with open(urlFileName, "r") as f:
    #     storedUrls = json.loads(f.read())

    for url in foundUrls:
        urlEnding = url.replace("https://www.mtgo.com/decklist/", "")
        if urlEnding not in storedUrls["completed"] and urlEnding not in storedUrls["failed"]["dead"]:
            newUrls.append(url)

    if date in storedUrls["failed"]["listing"]:
        storedUrls["failed"]["listing"].remove(date)

    with open(urlFileName, "wb") as f:
            f.write(json.dumps(storedUrls))

    return newUrls

def scrapeUrlsByMonth(datasetFile: str, format: str, skip: bool, grace: Optional[int] = 7, startDate: Optional[str] = None, endDate: Optional[str] = None) -> None:
    """
    Scrape one or more months of data for one format, and add data to datasetFile
    date inputs should be like 'yyyy/mm'
    """

    if not skip:
        updateCardPropertiesDataset()

    format = format.capitalize()

    dates = []

    if startDate == None:
        # scrape the previous [grace] days to prevent coverage issues with automated usage
        startDate = (datetime.today() - timedelta(days=grace)).strftime("%Y/%m")

    if endDate == None:
        endDate = datetime.today().strftime("%Y/%m")

    if (startDate > endDate):
        print("Error: Start Date comes after End Date")
        return

    dates = utils.getDatesBetweenMonths(startDate, endDate)

    for date in dates:
        scrapeUrls(datasetFile, getNewUrls(datasetFile, format, date))

def retryErroredUrls(dsPath: str, format: str):
    urlPath = dsPath.replace(".json", "_urls.json")
    with open(urlPath, "r") as f:
        urls = json.loads(f.read())
    
    
    numFailedEvents = len(urls["failed"]["event"])
    numFailedListings = len(urls["failed"]["listing"])

    for date in urls["failed"]["listing"]:
        scrapeUrls(dsPath, getNewUrls(dsPath, format, date))

        # Get updated urls after listing retries have occurred
    if numFailedEvents > 0:
        with open(urlPath, "r") as f:
            urls = json.loads(f.read())
    fullUrls = ["https://www.mtgo.com/decklist/" + urlEnding for urlEnding in urls["failed"]["event"]]

    scrapeUrls(dsPath, fullUrls)

    # Get updated urls after retries have occurred
    with open(urlPath, "r") as f:
        urls = json.loads(f.read())

    newNumEvents = len(urls["failed"]["event"])
    newNumListings = len(urls["failed"]["listing"])

    print(f"Number of urls retried:")
    print(f"Months: {numFailedListings}")
    print(f"Events: {numFailedEvents}")
    print()
    print(f"Number of urls that need to be retried again:")
    print(f"Months: {newNumListings}")
    print(f"Events: {newNumEvents}")


def createFileIfNotExist(filePath: str, content: any) -> None:
    if not path.isfile(filePath):
        with open(filePath, "wb+") as f:
            f.write(json.dumps(content))

def createDatasetFileIfNotExist(datasetFile: str) -> None:
    createFileIfNotExist(datasetFile, [])

def createUrlFileIfNotExist(urlFile: str) -> None:
    createFileIfNotExist(urlFile, {"completed": [], "failed": {"listing": [], "event": [], "dead": []}})
