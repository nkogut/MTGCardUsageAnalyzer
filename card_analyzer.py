import orjson as json
from datetime import *
from typing import Union, Optional
import string

DECK_ENTRY = dict[str, Union[str, dict[str, int]]]
DATASET_CHUNK_TYPE = list[DECK_ENTRY]
EVENT_TYPES = { "league": ["league", "gold", "daily"],
                "scheduled": ["prelim", "challenge", "ptq", "championship", "qualifier", "playoff", "finals", "last-chance"]}
SEARCH_IN_DEFAULT = ["main", "side"]

def loadDataset(dataset: str) -> DATASET_CHUNK_TYPE:
    # The dataset is a list of dictionaries, each of which represents 1 deck entry
    with open(dataset, "r") as f:
        return json.loads(f.read())

def displayDecks(decks: DATASET_CHUNK_TYPE | None) -> str:
    if decks is None:
        decks = []

    with open("Data/card_properties.json", "r") as f:
        cardProperties = json.loads(f.read())
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

    for location in searchIn:
        # Faster to search string than search each element
        cards = "@".join(decklist[location].keys())
        
        for b in blacklist:
            if b in cards:
                return False
            
        for w in remainingWhitelist:
            if w in cards:
                if leftToMatch <= 1:
                    return True
                remainingWhitelist.remove(w)
                leftToMatch -= 1
                
    return leftToMatch == 0

def getCardPrevalence(sample: str) -> string:
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
    maxCardLen = 0
    output = ""

    for location in SEARCH_IN_DEFAULT:
        locDict = prevalenceDict[location]
        for deck in sample:
            for card in deck[location]:
                if card in locDict:
                    locDict[card][0] +=  1
                    locDict[card][1] += deck[location][card]
                else:
                    locDict[card] = [1, deck[location][card]]
        
        maxCardLen = max(maxCardLen, len(max(locDict.keys(), key=lambda x: len(x))))

    maxQuantityLen = len(str(max(prevalenceDict["main"].values(), key=lambda x: x[0])[0]))

    # Add maindeck or sideboard to output
    for location in SEARCH_IN_DEFAULT:
        if location == "side":
            output += "\n\n---SIDEBOARD---\n"

        # Shorten long DFC names
        prevalenceDict[location] = {(k.split(" //")[0] + " // ...") if (" //" in k) else k: v for k, v in prevalenceDict[location].items()}
        quantityDescending = sorted(prevalenceDict[location].items(), key=lambda x: x[1][0], reverse=True)

        for card, quantity in quantityDescending:
            percentage = ((quantity[0] / numDecks) * 100)
            avg = (quantity[1] / quantity[0])
            output += f"\n{string.capwords(card):<{maxCardLen}} | {quantity[0]:>{maxQuantityLen}} decks | {percentage:.2f}% | {avg:.2f} avg"

    return output

