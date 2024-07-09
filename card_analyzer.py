import json
from datetime import *
from typing import Union, Optional

DATASET_CHUNK_TYPE = list[dict[str, Union[str, dict[str, int]]]]

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

            if card in deck['maindeck']:
                deck['maindeck']['Gifted Aetherborn'] = deck['maindeck'][card]
                del deck['maindeck'][card]

            if card in deck['sideboard']:
                deck['sideboard']['Gifted Aetherborn'] = deck['sideboard'][card]
                del deck['sideboard'][card]

        output += f"\n {deck['player']} {deck['url']}"
        try:
            maindeck = sorted(deck['maindeck'].keys(), key=lambda x: card_properties[x]['cmc'])
            sideboard = sorted(deck['sideboard'].keys(), key=lambda x: card_properties[x]['cmc'])
        except KeyError:
            # If an error occurs (rare), just display the deck without sorting by CMC
            pass

        for card in maindeck:
            try:
                output += f"\n{deck['maindeck'][card]} {card} - {card_properties[card]['mana_cost']}"
            except KeyError:
                output += f"\n{card} - error retrieving CMC or quantity"
        output += "\n------ SIDEBOARD ------"
        for card in sideboard:
            try:
                output += f"\n{deck['sideboard'][card]} {card} - {card_properties[card]['mana_cost']}"
            except KeyError:
                output += f"\n{card} - error retrieving CMC or quantity"
        output += "\n------ END OF DECK ------"
    return output

def find_decks(dataset: DATASET_CHUNK_TYPE,
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
    if search_in is None:
        search_in = ["maindeck", "sideboard"]
    if event_type is None:
        event_type = ["league", "scheduled"]

    found_decks = []
    decks_in_period = []  # For "% of all decks" feature
    for decklist in dataset:
        deck_date = decklist['date'].split("-")
        deck_date = date(int(deck_date[-3]), int(deck_date[-2]), int(deck_date[-1][:2]))
        if min_date <= deck_date <= max_date:
            decks_in_period.append(decklist)
    for decklist in decks_in_period:
        if player:
            if player.lower() not in decklist["player"].lower():
                continue

        # Get keywords that define event types to classify decklists by based on the chosen deck type categories
        event_keywords = []
        EVENT_TYPES = {"league": ["league", "daily-swiss"],
                       "scheduled": ["prelim", "challenge", "ptq", "championship", "qualifier", "playoff", "finals", "last-chance"]}

        for k, v in EVENT_TYPES.items():
            if k in event_type:
                event_keywords += v

        if not decklist['url'].split("-")[1] in event_keywords:
            continue
        matched_cards = []
        blacklisted_cards = []
        for location in search_in:
            for card in decklist[location]:
                for b in blacklist:
                    if b in card:
                        blacklisted_cards.append(card)
                for w in whitelist:
                    if w in card:  # Allow for partial matches with abbreviated names. ex. Fable of the gets mirror-breaker ...
                        matched_cards.append(card)
        if len(matched_cards) == len(whitelist) and len(blacklisted_cards) == 0:
            found_decks.append(decklist)
    return found_decks


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
        search_in = ["maindeck", "sideboard"]

    num_decks = len(sample)
    prevalence_dict_main = {}
    prevalence_dict_side = {}

    for deck in sample:
        if "maindeck" in search_in:
            for card in deck["maindeck"]:
                if card in prevalence_dict_main:
                    prevalence_dict_main[card][0] = prevalence_dict_main[card][0] + 1
                    prevalence_dict_main[card][1] = prevalence_dict_main[card][1] + deck["maindeck"][card]
                else:
                    prevalence_dict_main[card] = [1, deck["maindeck"][card]]
        if "sideboard" in search_in:
            for card in deck["sideboard"]:
                if card in prevalence_dict_side:
                    prevalence_dict_side[card][0] = prevalence_dict_side[card][0] + 1
                    prevalence_dict_side[card][1] = prevalence_dict_side[card][1] + deck["sideboard"][card]
                else:
                    prevalence_dict_side[card] = [1, deck["sideboard"][card]]

    output = ""
    for card, quantity in sorted(prevalence_dict_main.items(), key=lambda x: x[1][0], reverse=True):
        output += f"\n{card} - {quantity[0]} - {((quantity[0] / num_decks) * 100):.2f}% - {(quantity[1] / quantity[0]):.2f} average # played "
    output += "\n\n---SIDEBOARD---\n"
    for card, quantity in sorted(prevalence_dict_side.items(), key=lambda x: x[1][0], reverse=True):
        output += f"\n{card} - {quantity[0]} - {((quantity[0] / num_decks) * 100):.2f}% - {(quantity[1] / quantity[0]):.2f} average # played "
    return output

if __name__ == "__main__":
    dataset = load_dataset("Data/full_modern.json")

    # Example:
    # print(find_card_prevalence(find_decks(dataset=dataset,
    #                                       min_date=date(2023, 12, 4),
    #                                       whitelist=["The Rack"],
    #                                       event_type=["scheduled"])))

