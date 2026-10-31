import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import orjson as json
import requests
import gzip
from os import path
from datetime import *
from typing import Optional
from unidecode import unidecode
import utils
from collections import defaultdict, Counter
import pandas as pd
from pathlib import Path
from config import AGG_PLAY_RATE_PATH, AGG_START_DATE

import chromedriver_autoinstaller

CARD_TYPE_SEPARATORS = ["Creature (", "Land (", "Instant (", "Sorcery (", "Artifact (", "Enchantment (", "Planeswalker (",
                        "Other (", "Rarity", "Cards"]
''' 
Notes on other types: 
Battles are "Other ("
Tribal / Kindred are no longer used (they just use the other type)
"Cards" follows the quantity of maindeck cards and doses not have a "(". No legal cards have a name that conflicts with this weaker separator
'''

DRIVER_TIMEOUT = 4

chromedriver_autoinstaller.install()
chromeOptions = Options()
chromeOptions.add_argument("--headless")
chromeOptions.add_argument("--log-level=3") # Ignore unimpactful errors
chromeOptions.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2,}) # Prevent images from loading
chromeOptions.add_argument("--no-sandbox") # Attempt to fix linux error
chromeOptions.add_argument("--disable-dev-shm-usage") # Attempt to fix linux error

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
    re.raise_for_status()
    bulkDatasetLink = re.text.split("Oracle Cards")[1]
    bulkDatasetLink = bulkDatasetLink.split('href="')[1].split('">')[0]
    # e.g. https://data.scryfall.io/oracle-cards/oracle-cards-20260827090202.jsonl.gz

    # call api for that file
    re = requests.get(bulkDatasetLink, stream=True)
    re.raise_for_status()

    out = {}
    with gzip.GzipFile(fileobj=re.raw) as f:
        for line in f:
            c = json.loads(line)

            if c["set_type"] in ["vanguard", "token", "memorabilia", "alchemy", "minigame"]:
                continue
            if c["layout"] in ["art_series", "planar", "scheme"]:
                continue

            name = c["name"]
            lowerName = unidecode(name).lower().split(" //")[0]
            uri = c["scryfall_uri"]
            type = c["type_line"]
            cmc = c["cmc"]

            
            if "card_faces" in c.keys():
                front = c["card_faces"][0]
                back = c["card_faces"][1]

                if back["mana_cost"] == "":
                    back["mana_cost"] == "None"
                
                if back["mana_cost"]:
                    manaCost = " // ".join([front["mana_cost"], back["mana_cost"]])
                else:
                    manaCost = front["mana_cost"]
                oracle = "\n//\n".join([front["oracle_text"], back["oracle_text"]])

            else:

                if "mana_cost" in c:
                    manaCost = c["mana_cost"]
                else:
                    manaCost = "None"

                oracle = c["oracle_text"]
            
            out[lowerName] = {"displayName": name, "type": type, "uri": uri, "manaCost": manaCost, "cmc": cmc, "oracle": oracle}


    with open("Data/card_properties.json", "wb") as f:
        f.write(json.dumps(out))

    print("successfully updated card properties dataset from Scryfall\n")

def scrapeUrls(datasetFile: str, urls: list[str], killFailures: bool = False) -> None:
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
    daily_counts = defaultdict(Counter)

    print(f"Scraping {len(urls)} events")
    for url in urls:
        urlEnding = url.replace("https://www.mtgo.com/decklist/", "")
        try:
            driver.get(url)

            # If decklists-list class if found then the driver must have been redirected due to the url being dead
            WebDriverWait(driver, DRIVER_TIMEOUT).until(lambda driver: driver.find_elements(By.CLASS_NAME, "decklist-item-page") 
                                                        or driver.find_elements(By.CLASS_NAME, "decklist-title"))
            
            content = driver.find_elements(By.CLASS_NAME, 'decklist')
            if len(content) == 0:
                if len(driver.find_elements(By.CLASS_NAME, 'decklist-posted-on')) != 0: 
                    # The page definitely loaded, but no decks found
                    # This can happen with any event type
                    print(f"{url} has no decks. Killing it.")
                    deadUrls.append(urlEnding)
                    continue
                print(f"No decks found at {url} Please retry it")

                if killFailures:
                    deadUrls.append(urlEnding)
                else:
                    erroredUrls.append(urlEnding)
                continue
            elif driver.find_elements(By.CLASS_NAME, 'decklists-page'):
                # Its common to randomly not load a valid page and get redirected to the month's page.
                print("WAS REDIRECTED " + url)
                if killFailures:
                    deadUrls.append(urlEnding)
                else:
                    erroredUrls.append(urlEnding)
            else:
                # Successfully loaded a page with decks on it
                print(f"Gathering {len(content)} decks from", url)
                scrapedUrls.append(urlEnding)
            
        except selenium.common.exceptions.TimeoutException:
            print(f"Failed to reach {url} Please retry it")
            # This page just never loaded. It may or may not exist
            if killFailures:
                deadUrls.append(urlEnding)
            else:
                erroredUrls.append(urlEnding)
            continue

        for decklist in content:
            deckContents = decklist.text
            deckContents = deckContents.split("\n")
            deckDate = dateFromUrl(urlEnding)
            player = deckContents[0]
            player = unidecode(player.split(" ")[0])
            deck = {'date': deckDate, "player": player, "url": urlEnding, "main": {}, "side": {}}
            today_timestamp = pd.to_datetime(deck["date"])
            
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

                    if today_timestamp >= AGG_START_DATE:
                        daily_counts[today_timestamp][card] += int(quantity)

            numDecks += 1
            decks.append(deck)

    rows = []
    for date, counter in daily_counts.items():
        for card, count in counter.items():
            rows.append((date, datasetName, card, count))

    if rows:
        new_df = pd.DataFrame(rows, columns=["date", "format", "card", "count"])
        new_df = new_df.set_index(["date", "format", "card"])

        # merge with existing data
        if Path(AGG_PLAY_RATE_PATH).exists():
            df = pd.read_parquet(AGG_PLAY_RATE_PATH)
            df = (pd.concat([df, new_df]))
        else:
            df = new_df.copy()

        df = (df.groupby(level=["date", "format", "card"]).sum().sort_index()
)
        df.to_parquet(AGG_PLAY_RATE_PATH, compression="snappy")
    

    createDatasetFileIfNotExist(datasetFile)
    with open(datasetFile, "r") as f:
        storedDecks = json.loads(f.read()) 
        storedDecks += decks
        storedDecks = sorted(storedDecks, key=lambda x: x["date"])

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
    numDead = len(deadUrls)
    if (numErrors) > 0:
        print(f"\nError: Failed to reach {numErrors} Url{'s' if (numErrors > 1) else ''}. Please try them again with 'python scrape.py <dataset> <format> -retry'\n")
    if (numDead) > 0:
        print(f"\nKilled {numDead} urls")

    with open(urlFileName, "wb") as f:
        f.write(json.dumps(storedUrls))


def dateFromUrl(url: str) -> str:
    deckDate = url.split("-")
    year = int(deckDate[-3])
    month = int(deckDate[-2])
    day = int(deckDate[-1][:2])

    return f"{year}-{month:02d}-{day:02d}"

def getNewUrls(datasetFile: str, format: str, date: str, killFailures: bool = False) -> list[str]:
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
        if killFailures:
            storedUrls["failed"]["dead"] = list(set([date] + storedUrls["failed"]["dead"]))
            if date in storedUrls["failed"]["listing"]:
                storedUrls["failed"]["listing"].remove(date)
        else:
            storedUrls["failed"]["listing"] = list(set([date] + storedUrls["failed"]["listing"]))
        
        with open(urlFileName, "wb") as f:
            f.write(json.dumps(storedUrls))
        return []

    for l in content:
        foundUrls.append(l.get_attribute("href"))

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

def retryErroredUrls(dsPath: str, format: str, killFailures: bool = False):
    urlPath = dsPath.replace(".json", "_urls.json")
    with open(urlPath, "r") as f:
        urls = json.loads(f.read())
    
    numFailedEvents = len(urls["failed"]["event"])
    numFailedListings = len(urls["failed"]["listing"])

    for date in urls["failed"]["listing"]:
        scrapeUrls(dsPath, getNewUrls(dsPath, format, date, killFailures=killFailures), killFailures=killFailures)

        # Get updated urls after listing retries have occurred
    if numFailedEvents > 0:
        with open(urlPath, "r") as f:
            urls = json.loads(f.read())
    fullUrls = ["https://www.mtgo.com/decklist/" + urlEnding for urlEnding in urls["failed"]["event"]]

    scrapeUrls(dsPath, fullUrls, killFailures=killFailures)

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
