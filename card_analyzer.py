import json
from datetime import *
from typing import Union, Optional

DECK_ENTRY = dict[str, Union[str, dict[str, int]]]
DATASET_CHUNK_TYPE = list[DECK_ENTRY]
EVENT_TYPES = { "league": ["league", "gold", "daily"],
                "scheduled": ["prelim", "challenge", "ptq", "championship", "qualifier", "playoff", "finals", "last-chance"]}
SEARCH_IN_DEFAULT = ["main", "side"]

def loadDataset(dataset: str) -> DATASET_CHUNK_TYPE:
    # The dataset is a list of dictionaries, each of which represents 1 deck entry
    with open(dataset, "r") as f:
        return json.load(f)

def displayDecks(decks: DATASET_CHUNK_TYPE | None) -> str:
    if decks is None:
        decks = []

    with open("Data/card_properties.json", "r") as f:
        cardProperties = json.load(f)
    output = ""

    for deck in decks:
        # For non-english characters that are represented differently on different mtgo.com pages: replace with a safe
        # card name in the rare case that some are stored inconsistently in older versions of the database
        brokenNames = ['Troll of Khazad-dÃ»m', "LÃ³rien Revealed"]
        for card in brokenNames:
            for location in SEARCH_IN_DEFAULT:

                if card in deck[location]:
                    deck[location]['Gifted Aetherborn'] = deck[location][card]
                    del deck[location][card]

        output += f"\n {deck['player']} {deck['url']}"
        try:
            main = sorted(deck['main'].keys(), key=lambda x: cardProperties[x]['cmc'])
            side = sorted(deck['side'].keys(), key=lambda x: cardProperties[x]['cmc'])
        except KeyError:
            # The Data/card_properties.json dataset is out of date
            main = deck['main']
            side = deck['side']

        for card in main:
            try:
                output += f"\n{deck['main'][card]} {card} - {cardProperties[card]['mana']}"
            except KeyError:
                output += f"\n{card} - error retrieving CMC or quantity"
        output += "\n------ side ------"
        for card in side:
            try:
                output += f"\n{deck['side'][card]} {card} - {cardProperties[card]['mana']}"
            except KeyError:
                output += f"\n{card} - error retrieving CMC or quantity"
        output += "\n------ END OF DECK ------"
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

    dataset = loadDataset(dataset)

    foundDecks = []
    decksInPeriod = []  # For "% of all decks" feature
    for decklist in dataset:
        deckDate = decklist['date'][:10]
        deckDate = datetime.strptime(deckDate, "%Y-%m-%d").date()
        if minDate <= deckDate <= maxDate:
            decksInPeriod.append(decklist)
    
    for decklist in decksInPeriod:
        if player:
            if player.lower() not in decklist["player"].lower():
                continue

        # Get keywords that define event types to classify decklists by based on the chosen deck type categories
        eventKeywords = []

        for k, v in EVENT_TYPES.items():
            if k in eventType:
                eventKeywords += v

        event = decklist['url'].split("-")[1]
        if event not in eventKeywords:
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
    for location in searchIn:
        for card in decklist[location]:
            
            for b in blacklist:
                if b in card:
                    return False
                
            for w in remainingWhitelist:
                if w in card: 
                    remainingWhitelist.remove(w)
                    leftToMatch -= 1
                    if leftToMatch == 0:
                        return True
    return leftToMatch == 0 # In case whitelist = []

def getCardPrevalence(sample: DATASET_CHUNK_TYPE):
    """
    Calculates the prevalence of each card across all decks in sample and lists them in this order
    sample parameter should be passed from getDecks()
    Output looks like:
    Most prevalent card - # copies in sample - % of decks it appears in - Average # played in decks it appeared in
    """
    if not sample:
        return "No decks in sample"

    numDecks = len(sample)
    prevalenceDict = {"main": {}, "side": {}}
    
    output = ""

    for location in SEARCH_IN_DEFAULT:
        locDict = prevalenceDict[location]
        for deck in sample:
            for card in deck[location]:
                if card in locDict:
                    locDict[card][0] = locDict[card][0] + 1
                    locDict[card][1] = locDict[card][1] + deck[location][card]
                else:
                    locDict[card] = [1, deck[location][card]]

        # Add maindeck or sideboard to output
        if location == "side":
            output += "\n\n---SIDEBOARD---\n"

        for card, quantity in sorted(locDict.items(), key=lambda x: x[1][0], reverse=True):
            output += f"\n{card.title()} - {quantity[0]} - {((quantity[0] / numDecks) * 100):.2f}% - {(quantity[1] / quantity[0]):.2f} average # played "

    return output
