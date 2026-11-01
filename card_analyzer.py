import orjson as json
from datetime import *
from typing import Union, Optional
import string
import scraper
import config
import unidecode
import requests
import gzip

from pathlib import Path

DECK_ENTRY = dict[str, Union[str, dict[str, int]]]
DATASET_CHUNK_TYPE = list[DECK_ENTRY]

def load_dataset(dataset: Path) -> DATASET_CHUNK_TYPE:
    # The dataset is a list of dictionaries, each of which represents 1 deck entry
    return dataset.read_bytes()

def display_decks(decks: DATASET_CHUNK_TYPE | None) -> str:
    output = ""
    card_properties = load_card_properties(force=False)
    if decks is None:
        decks = []

    for deck in decks:
        output += f"\n {deck['player']} {deck['url']}"
        try:
            main = sorted(deck['main'].keys(), key=lambda x: card_properties[x]['cmc'])
            side = sorted(deck['side'].keys(), key=lambda x: card_properties[x]['cmc'])
        except KeyError:
            print("Error: The card properties cache is out of date. Please update it with 'python analyze.py -fprops'")
            main = deck['main']
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
        output += "\n------ END OF DECK ------\n"
    return output

def get_decks(dataset_path: Path,
               whitelist: Optional[list[str]] = None,
               blacklist: Optional[list[str]] = None,
               player: Optional[str | None] = None,
               min_date: Optional[datetime.date] = config.DEFAULT_MIN_DATE,
               max_date: Optional[datetime.date] = config.DEFAULT_MAX_DATE,
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
        search_in = config.SEARCH_IN_DEFAULT

    event_type = [v.lower() for v in event_type] if event_type else config.DEFAULT_EVENT_TYPES

    # Faster to search string than search each element
    matchable_events = "@".join([("@".join(config.EVENT_TYPES[k])) for k in event_type]) 

    dataset = json.loads(dataset_path.read_bytes())
    found_decks = []

    if player:
        player = player.lower()

    min_date = min_date.strftime(config.DATE_FMT_DECK)
    max_date = max_date.strftime(config.DATE_FMT_DECK)
    dataset = [deck for deck in dataset if min_date <= deck["date"] <= max_date]

    for decklist in dataset:
        if player and player not in decklist["player"].lower():
            continue

        event = decklist['url'].split("-")[1]
        if event not in matchable_events:
            continue

        if not should_accept_deck(search_in, decklist, whitelist, blacklist):
            continue
        
        found_decks.append(decklist)

    return found_decks

def should_accept_deck(search_in: list[str], decklist: DECK_ENTRY, whitelist: list[str], blacklist: list[str]) -> bool:
    """
    Checks whether or not a deck should be included in a search based on whitelist/blacklist.
    Allows partial names in whitelist/blacklist (e.g. "bolt")
    """
    if not whitelist and not blacklist:
        return True
    
    left_to_match = len(whitelist)
    cards = "@".join(["@".join(decklist[location].keys()) for location in search_in])

    for b in blacklist:
        if b in cards:
            return False
        
    for w in whitelist:
        if w in cards:
            if left_to_match <= 1:
                return True
            left_to_match -= 1
                
def get_card_prevalence(sample: str, show_types: Optional[list[str]] = None) -> string:
    """
    Calculates the prevalence of each card across all decks in sample and lists them in this order
    sample parameter should be passed from get_decks()
    Output looks like:
    Most prevalent card - # copies in sample - % of decks it appears in - Average # played in decks it appeared in
    """
    
    if not sample:
        return "No decks in sample"

    card_properties = load_card_properties(force=False)
    
    if show_types:
        show_types = [string.capwords(t) for t in show_types]

    # Use this list of all cards in card_properties to make sure an invalid key is never used.
    # This would only occur if the Scryfall API was briefly out of date when a new set is released. 
    # Failing to check against this will destroy the dictionary comprehensions below  
    recognizeable_cards = card_properties.keys()

    num_decks = len(sample)
    prevalence_dict = {"main": {}, "side": {}}
    max_card_len = 0
    output = ""
    unrecoginzable_cards = [] # Track cards that cannot match card_properties so they do not get logged multiple times

    for location in config.SEARCH_IN_DEFAULT:
        loc_dict = prevalence_dict[location]
        for deck in sample:
            for card in deck[location]:
                if card not in recognizeable_cards:
                    if card not in unrecoginzable_cards:
                        unrecoginzable_cards.append(card)
                        print(f"Error: unable to identify {card}. Please update card_properties.json.")
                    continue
                if card in loc_dict:
                    loc_dict[card][0] +=  1
                    loc_dict[card][1] += deck[location][card]
                else:
                    loc_dict[card] = [1, deck[location][card]]
        
        longest_card_name = max(loc_dict.keys(), key=lambda x: len(card_properties[x]["display_name"]))
        max_card_len = max(max_card_len, len(card_properties[longest_card_name]["display_name"]))

    max_quantity_len = len(str(max(prevalence_dict["main"].values(), key=lambda x: x[0])[0]))            

    # Add maindeck or sideboard to output
    for location in config.SEARCH_IN_DEFAULT:
        if location == "side":
            output += "\n\n---SIDEBOARD---\n"

        if show_types:
            def keep(name):
                for type in show_types:
                    if type in card_properties[name]["type"]:
                        return True
                return False
            prevalence_dict[location] = {k:v for k,v in prevalence_dict[location].items() if (keep(k))}
        

        quantity_descending = sorted(prevalence_dict[location].items(), key=lambda x: x[1][0], reverse=True)

        for card, quantity in quantity_descending:
            percentage = ((quantity[0] / num_decks) * 100)
            avg = (quantity[1] / quantity[0])
            output += f"\n{card_properties[card]['display_name']:<{max_card_len}} | {quantity[0]:>{max_quantity_len}} decks | {percentage:>5.2f}% | {avg:.2f} avg"

    return output

def get_card_prevalence_for_goat(sample: dict, recognizeable_cards: Optional[list[str]] = None) -> dict:
    
    if not sample:
        return "No decks in sample"

    if not recognizeable_cards:
        card_properties = load_card_properties(force=False)
        recognizeable_cards = card_properties.keys()
    prevalence_dict = {card: 0 for card in recognizeable_cards}

    num_decks = 0
    num_cards = 0
    for location in config.SEARCH_IN_DEFAULT:
        for deck in sample:
            num_decks += 1
            for card in deck[location]:
                if card not in recognizeable_cards:
                    continue
                # Count total cards, regardless of loc
                num_cards += deck[location][card]
                prevalence_dict[card] += deck[location][card]
    
    prevalence_dict = {card: float(qty * num_decks) / num_cards for card, qty in prevalence_dict.items()}

    return prevalence_dict

def load_card_properties(force):
    if not config.CARD_PROPERTIES_PATH.is_file() or force:
        print("Updating Card Properties dataset")
        scraper.update_card_properties_dataset()

    return json.loads(config.CARD_PROPERTIES_PATH.read_bytes())

def update_card_properties_dataset(self) -> None: 
        """Call the Scryfall API to update the local cache of card metadata."""
        response = requests.get(config.SCRYFALL_BULK_DATA_URL, timeout=config.SCRYFALL_CATALOG_TIMEOUT)
        response.raise_for_status()
        
        bulk_dataset_link = response.text.split("Oracle Cards")[1].split('href="')[1].split('">')[0]

        response = requests.get(bulk_dataset_link, stream=True, timeout=config.SCRYFALL_BULK_DATA_TIMEOUT)
        response.raise_for_status()

        out = {}
        with gzip.GzipFile(fileobj=response.raw) as f:
            for line in f:
                c = json.loads(line)

                if c.get("set_type") in config.SCRYFALL_IGNORED_SET_TYPES or c.get("layout") in config.SCRYFALL_IGNORED_LAYOUTS:
                    continue

                name = c["name"]
                lower_name = unidecode(name).lower().split(" //")[0]
                
                if faces := c.get("card_faces"):
                    front, back = faces[0], faces[1]
                    mana_cost = f"{front.get('mana_cost', '')} // {back['mana_cost']}" if back.get("mana_cost") else front.get("mana_cost", "")
                    oracle = f"{front.get('oracle_text', '')}\n//\n{back.get('oracle_text', '')}"
                else:
                    mana_cost = c.get("mana_cost", "None")
                    oracle = c.get("oracle_text", "")
                
                out[lower_name] = {
                    "display_name": name, 
                    "type": c.get("type_line", ""), 
                    "uri": c.get("scryfall_uri", ""), 
                    "mana_cost": mana_cost, 
                    "cmc": c.get("cmc", 0.0), 
                    "oracle": oracle
                }

        config.CARD_PROPERTIES_PATH.write_bytes(json.dumps(out))
