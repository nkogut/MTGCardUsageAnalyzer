import json
from datetime import *
from typing import Union, Optional

DECK_ENTRY = dict[str, Union[str, dict[str, int]]]
DATASET_CHUNK_TYPE = list[DECK_ENTRY]
EVENT_TYPES = { "league": ["league", "gold", "daily"],
                "scheduled": ["prelim", "challenge", "ptq", "championship", "qualifier", "playoff", "finals", "last-chance"]}

def load_dataset(dataset: str) -> DATASET_CHUNK_TYPE:
    # The dataset is a list of dictionaries, each of which represents 1 deck entry
    with open(dataset, "r") as f:
        return json.load(f)

def display_decks(decks: DATASET_CHUNK_TYPE | None) -> str:
    if decks is None:
        decks = []

    with open("Data/card_properties.json", "r") as f:
        card_properties = json.load(f)
    output = ""

    for deck in decks:
        # For non-english characters that are represented differently on different mtgo.com pages: replace with a safe
        # card name in the rare case that some are stored inconsistently in older versions of the database
        broken_names = ['Troll of Khazad-dÃ»m', "LÃ³rien Revealed"]
        for card in broken_names:

            if card in deck['main']:
                deck['main']['Gifted Aetherborn'] = deck['main'][card]
                del deck['main'][card]

            if card in deck['side']:
                deck['side']['Gifted Aetherborn'] = deck['side'][card]
                del deck['side'][card]

        output += f"\n {deck['player']} {deck['url']}"
        try:
            main = sorted(deck['main'].keys(), key=lambda x: card_properties[x]['cmc'])
            side = sorted(deck['side'].keys(), key=lambda x: card_properties[x]['cmc'])
        except KeyError:
            # The card_properties dataset is out of date
            main =deck['main']
            side = deck['side']

        for card in main:
            try:
                output += f"\n{deck['main'][card]} {card} - {card_properties[card]['mana_cost']}"
            except KeyError:
                output += f"\n{card} - error retrieving CMC or quantity"
        output += "\n------ side ------"
        for card in side:
            try:
                output += f"\n{deck['side'][card]} {card} - {card_properties[card]['mana_cost']}"
            except KeyError:
                output += f"\n{card} - error retrieving CMC or quantity"
        output += "\n------ END OF DECK ------"
    return output

def find_decks(dataset: str,
               whitelist: Optional[list[str]] = None,
               blacklist: Optional[list[str]] = None,
               player: Optional[str | None] = None,
               min_date: Optional[datetime.date] = date(1900, 1, 1),
               max_date: Optional[datetime.date] = date(2100, 1, 1),
               search_in: Optional[list[str]] = None,
               event_type: Optional[list[str]] = None) -> DATASET_CHUNK_TYPE:
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

    if search_in is None:
        search_in = ["main", "side"]

    if event_type is None:
        event_type = ["league", "scheduled"]

    dataset = load_dataset(dataset)

    found_decks = []
    decks_in_period = []  # For "% of all decks" feature
    for decklist in dataset:
        deck_date = decklist['date'][:10]
        deck_date = datetime.strptime(deck_date, "%Y-%m-%d").date()
        # deck_date = decklist['date'].split("-")
        # deck_date = date(int(deck_date[-3]), int(deck_date[-2]), int(deck_date[-1][:2]))
        if min_date <= deck_date <= max_date:
            decks_in_period.append(decklist)
    
    for decklist in decks_in_period:
        if player:
            if player.lower() not in decklist["player"].lower():
                continue

        # Get keywords that define event types to classify decklists by based on the chosen deck type categories
        event_keywords = []

        for k, v in EVENT_TYPES.items():
            if k in event_type:
                event_keywords += v

        event = decklist['url'].split("-")[1]
        if event not in event_keywords:
            continue

        if not shouldAcceptDeck(search_in, decklist, whitelist, blacklist):
            continue
        
        found_decks.append(decklist)

    return found_decks

def shouldAcceptDeck(search_in: list[str], decklist: DECK_ENTRY, whitelist: list[str], blacklist: list[str]) -> bool:
    """
    Checks whether or not a deck should be included in a search based on whitelist/blacklist.
    Allows partial names in whitelist/blacklist (e.g. "bolt")
    """
    remainingWhitelist = whitelist.copy()
    leftToMatch = len(whitelist)
    for location in search_in:
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

def find_card_prevalence(sample: DATASET_CHUNK_TYPE, search_in: Optional[list[str]] = None):
    """
    Calculates the prevalence of each card across all decks in sample and lists them in this order
    sample parameter should be passed from find_decks()
    Output looks like:
    Most prevalent card - # copies in sample - % of decks it appears in - Average # played in decks it appeared in
    """
    if not sample:
        return "No decks in sample"

    if search_in is None:
        search_in = ["main", "side"]


    num_decks = len(sample)
    prevalence_dict_main = {}
    prevalence_dict_side = {}

    for deck in sample:
        if "main" in search_in:
            for card in deck["main"]:
                if card in prevalence_dict_main:
                    prevalence_dict_main[card][0] = prevalence_dict_main[card][0] + 1
                    prevalence_dict_main[card][1] = prevalence_dict_main[card][1] + deck["main"][card]
                else:
                    prevalence_dict_main[card] = [1, deck["main"][card]]
        if "side" in search_in:
            for card in deck["side"]:
                if card in prevalence_dict_side:
                    prevalence_dict_side[card][0] = prevalence_dict_side[card][0] + 1
                    prevalence_dict_side[card][1] = prevalence_dict_side[card][1] + deck["side"][card]
                else:
                    prevalence_dict_side[card] = [1, deck["side"][card]]

    output = ""
    for card, quantity in sorted(prevalence_dict_main.items(), key=lambda x: x[1][0], reverse=True):
        output += f"\n{card.title()} - {quantity[0]} - {((quantity[0] / num_decks) * 100):.2f}% - {(quantity[1] / quantity[0]):.2f} average # played "
    output += "\n\n---SIDEBOARD---\n"
    for card, quantity in sorted(prevalence_dict_side.items(), key=lambda x: x[1][0], reverse=True):
        output += f"\n{card.title()} - {quantity[0]} - {((quantity[0] / num_decks) * 100):.2f}% - {(quantity[1] / quantity[0]):.2f} average # played "
    return output
