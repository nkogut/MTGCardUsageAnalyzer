import orjson as json
from datetime import *
from typing import Union, Optional
from os import path
import string
import scraper
import config

DECK_ENTRY = dict[str, Union[str, dict[str, int]]]
DATASET_CHUNK_TYPE = list[DECK_ENTRY]

def loadDataset(dataset: str) -> DATASET_CHUNK_TYPE:
    # The dataset is a list of dictionaries, each of which represents 1 deck entry
    with open(dataset, "r") as f:
        return json.loads(f.read())

def displayDecks(decks: DATASET_CHUNK_TYPE | None) -> str:
    output = ""
    cardProperties = loadCardProperties(force=False)
    if decks is None:
        decks = []

    for deck in decks:
        output += f"\n {deck['player']} {deck['url']}"
        try:
            main = sorted(deck['main'].keys(), key=lambda x: cardProperties[x]['cmc'])
            side = sorted(deck['side'].keys(), key=lambda x: cardProperties[x]['cmc'])
        except KeyError:
            print("Error: The card properties cache is out of date. Please update it with 'python analyze.py -fprops'")
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
               minDate: Optional[datetime.date] = config.DEFAULT_MIN_DATE,
               maxDate: Optional[datetime.date] = config.DEFAULT_MAX_DATE,
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
        searchIn = config.SEARCH_IN_DEFAULT

    eventType = [v.lower() for v in eventType] if eventType else config.DEFAULT_EVENT_TYPES

    # Faster to search string than search each element
    matchableEvents = "@".join([("@".join(config.EVENT_TYPES[k])) for k in eventType]) 

    dataset = loadDataset(dataset)
    foundDecks = []

    if player:
        player = player.lower()

    minDate = minDate.strftime(config.DATE_FMT_DECK)
    maxDate = maxDate.strftime(config.DATE_FMT_DECK)
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
    if not whitelist and not blacklist:
        return True
    
    leftToMatch = len(whitelist)
    cards = "@".join(["@".join(decklist[location].keys()) for location in searchIn])

    for b in blacklist:
        if b in cards:
            return False
        
    for w in whitelist:
        if w in cards:
            if leftToMatch <= 1:
                return True
            leftToMatch -= 1
                
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

    for location in config.SEARCH_IN_DEFAULT:
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
    for location in config.SEARCH_IN_DEFAULT:
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

def getCardPrevalenceForGoat(sample: dict, recognizeableCards: Optional[list[str]] = None) -> dict:
    
    if not sample:
        return "No decks in sample"

    if not recognizeableCards:
        cardProperties = loadCardProperties(force=False)
        recognizeableCards = cardProperties.keys()
    prevalenceDict = {card: 0 for card in recognizeableCards}

    numDecks = 0
    numCards = 0
    for location in config.SEARCH_IN_DEFAULT:
        for deck in sample:
            numDecks += 1
            for card in deck[location]:
                if card not in recognizeableCards:
                    continue
                # Count total cards, regardless of loc
                numCards += deck[location][card]
                prevalenceDict[card] += deck[location][card]
    
    prevalenceDict = {card: float(qty * numDecks) / numCards for card, qty in prevalenceDict.items()}

    return prevalenceDict

def loadCardProperties(force):
    if not path.isfile(config.CARD_PROPERTIES_PATH) or force:
        print("Updating Card Properties dataset")
        scraper.updateCardPropertiesDataset()

    with open(config.CARD_PROPERTIES_PATH, "rb") as f:
        return json.loads(f.read())
