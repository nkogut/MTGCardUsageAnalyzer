import orjson as json
from datetime import *
from typing import Union, Optional
from os import path
import string
import scraper

DECK_ENTRY = dict[str, Union[str, dict[str, int]]]
DATASET_CHUNK_TYPE = list[DECK_ENTRY]
EVENT_TYPES = { "league": ["league", "gold", "daily"],
                "scheduled": ["prelim", "challenge", "ptq", "championship", "qualifier", "playoff", "finals", "last-chance"]}
SEARCH_IN_DEFAULT = ["main", "side"]
CARD_PROPERTIES_PATH = "Data/card_properties.json"


def loadDataset(dataset: str) -> DATASET_CHUNK_TYPE:
    # The dataset is a list of dictionaries, each of which represents 1 deck entry
    with open(dataset, "r") as f:
        return json.loads(f.read())


def displayDecks(decks: DATASET_CHUNK_TYPE | None) -> str:
    if decks is None:
        decks = []

    cardProperties = loadCardProperties(force=False)

    output = ""

    for deck in decks:
        output += f"\n {deck['player']} {deck['url']}"
        try:
            main = sorted(deck['main'].keys(), key=lambda x: cardProperties[x]['cmc'])
            side = sorted(deck['side'].keys(), key=lambda x: cardProperties[x]['cmc'])
        except KeyError:
            # The Data/card_properties.json dataset is out of date. In this case do not sort on cmc
            print("Error: Card Properties is out of date. Please update it with 'python analyze.py -fprops'")
            main = deck['main']
            side = deck['side']

        for card in main:
            try:
                output += f"\n{deck['main'][card]} {card} - {cardProperties[card]['manaCost']}"
            except KeyError:
                output += f"\n{card} - error retrieving CMC or quantity"
        output += "\n------ side ------"
        for card in side:
            try:
                output += f"\n{deck['side'][card]} {card} - {cardProperties[card]['manaCost']}"
            except KeyError:
                output += f"\n{card} - error retrieving CMC or quantity"
        output += "\n------ END OF DECK ------\n"
    return output


def getDecks(dataset: str,
               whitelist: Optional[list[str]] = None,
               blacklist: Optional[list[str]] = None,
               player: Optional[str | None] = None,
               minDate: Optional[datetime.date] = date(1900, 1, 1),
               maxDate: Optional[datetime.date] = date(2100, 1, 1),
               searchIn: Optional[list[str]] = None,
               eventType: Optional[list[str]] = None) -> DATASET_CHUNK_TYPE:
    """
    Gathers all decks matching criteria
    Outputs them in the same format as they appear in the dataset
    """

    # Handle unspecified parameters instead of using default mutable parameters
    if whitelist is None:
        whitelist = []
    if blacklist is None:
        blacklist = []

    whitelist = [v.lower() for v in whitelist]
    blacklist = [v.lower() for v in blacklist]

    if searchIn is None:
        searchIn = SEARCH_IN_DEFAULT

    if eventType is None:
        eventType = ["league", "scheduled"]
    else:
        eventType = [v.lower() for v in eventType]

    # Faster to search string than search each element
    matchableEvents = "@".join([("@".join(EVENT_TYPES[k])) for k in eventType]) 


    dataset = loadDataset(dataset)
    foundDecks = []

    minDate = str(minDate)
    maxDate = str(maxDate)
    if player:
        player = player.lower()

    dataset = [deck for deck in dataset if minDate <= deck["date"] <= maxDate]

    for decklist in dataset:
        if player and player not in decklist["player"].lower():
            continue

        event = decklist['url'].split("-")[1]
        if event not in matchableEvents:
            continue

        if not shouldAcceptDeck(searchIn, decklist, whitelist, blacklist):
            continue
        
        foundDecks.append(decklist)

    return foundDecks

def shouldAcceptDeck(searchIn: list[str], decklist: DECK_ENTRY, whitelist: list[str], blacklist: list[str]) -> bool:
    """
    Checks whether or not a deck should be included in a search based on whitelist/blacklist.
    Allows partial names in whitelist/blacklist (e.g. "bolt")
    """
    remainingWhitelist = whitelist.copy()
    leftToMatch = len(whitelist)
    blacklist = set(blacklist)
    cards = "@".join(["@".join(decklist[location].keys()) for location in searchIn])

    for b in blacklist:
        if b in cards:
            return False
        
    for w in remainingWhitelist:
        if w in cards:
            if leftToMatch <= 1:
                return True
            leftToMatch -= 1
                
    return leftToMatch == 0

def getCardPrevalence(sample: str, showTypes: Optional[list[str]] = None) -> string:
    """
    Calculates the prevalence of each card across all decks in sample and lists them in this order
    sample parameter should be passed from getDecks()
    Output looks like:
    Most prevalent card - # copies in sample - % of decks it appears in - Average # played in decks it appeared in
    """
    
    if not sample:
        return "No decks in sample"

    cardProperties = loadCardProperties(force=False)
    
    if showTypes:
            showTypes = [string.capwords(t) for t in showTypes]

    # Use this list of all cards in cardProperties to make sure an invalid key is never used.
    # This would only occur if the Scryfall API was briefly out of date when a new set is released. 
    # Failing to check against this will destroy the dictionary comprehensions below  
    recognizeableCards = cardProperties.keys()

    numDecks = len(sample)
    prevalenceDict = {"main": {}, "side": {}}
    maxCardLen = 0
    output = ""
    unrecoginzableCards = [] # Track cards that cannot match cardProperties so they do not get logged multiple times

    for location in SEARCH_IN_DEFAULT:
        locDict = prevalenceDict[location]
        for deck in sample:
            for card in deck[location]:
                if card not in recognizeableCards:
                    if card not in unrecoginzableCards:
                        unrecoginzableCards.append(card)
                        print(f"Error: unable to identify {card}. Please update card_properties.json.")
                    continue
                if card in locDict:
                    locDict[card][0] +=  1
                    locDict[card][1] += deck[location][card]
                else:
                    locDict[card] = [1, deck[location][card]]
        
        longestCardName = max(locDict.keys(), key=lambda x: len(cardProperties[x]["displayName"]))
        maxCardLen = max(maxCardLen, len(cardProperties[longestCardName]["displayName"]))

    maxQuantityLen = len(str(max(prevalenceDict["main"].values(), key=lambda x: x[0])[0]))            

    # Add maindeck or sideboard to output
    for location in SEARCH_IN_DEFAULT:
        if location == "side":
            output += "\n\n---SIDEBOARD---\n"

        if showTypes:
            def keep(name):
                for type in showTypes:
                    if type in cardProperties[name]["type"]:
                        return True
                return False
            prevalenceDict[location] = {k:v for k,v in prevalenceDict[location].items() if (keep(k))}
        

        quantityDescending = sorted(prevalenceDict[location].items(), key=lambda x: x[1][0], reverse=True)

        for card, quantity in quantityDescending:
            percentage = ((quantity[0] / numDecks) * 100)
            avg = (quantity[1] / quantity[0])
            output += f"\n{cardProperties[card]['displayName']:<{maxCardLen}} | {quantity[0]:>{maxQuantityLen}} decks | {percentage:>5.2f}% | {avg:.2f} avg"

    return output

def loadCardProperties(force):
    if not path.isfile(CARD_PROPERTIES_PATH) or force:
        print("Updating Card Properties dataset")
        scraper.updateCardPropertiesDataset()

    with open(CARD_PROPERTIES_PATH, "rb") as f:
        return json.loads(f.read())
