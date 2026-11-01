import orjson as json
from datetime import *
from typing import Union, Optional, TypedDict
import string
import config
import logging

from pathlib import Path

from card_metadata import CardMetadata

logger = logging.getLogger(__name__)

class DeckEntry(TypedDict):
    date: str
    player: str
    url: str
    main: dict[str, int]
    side: dict[str, int]

DATASET_CHUNK_TYPE = list[DeckEntry]

class DeckAnalyzer:
    """Analyzes card pairing and deck construction data for a particular metagame."""

    def __init__(self, dataset_path: Path, card_metadata: CardMetadata):
        self.dataset_path = dataset_path
        self.card_metadata = card_metadata
        self.dataset = json.loads(self.dataset_path.read_bytes())

    def query_decks(
        self,
        whitelist: Optional[list[str]] = None,
        blacklist: Optional[list[str]] = None,
        player: Optional[str] = None,
        min_date: Optional[date] = config.DEFAULT_MIN_DATE,
        max_date: Optional[date] = config.DEFAULT_MAX_DATE,
        search_in: Optional[list[str]] = None,
        event_types: Optional[list[str]] = None
    ) -> DATASET_CHUNK_TYPE:
        """Gather all decks matching the specified criteria."""
        whitelist = [v.lower() for v in (whitelist or [])]
        blacklist = [v.lower() for v in (blacklist or [])]
        search_in = search_in or config.SEARCH_IN_DEFAULT
        event_types = [v.lower() for v in event_types] if event_types else config.DEFAULT_EVENT_TYPES

        # Combine events into a string for efficient partial match testing
        matchable_events = "@".join(["@".join(config.EVENT_TYPES[k]) for k in event_types]) 
        
        if player:
            player = player.lower()

        min_date_str = min_date.strftime(config.DATE_FMT_DECK)
        max_date_str = max_date.strftime(config.DATE_FMT_DECK)
        
        filtered_dataset = [deck for deck in self.dataset if min_date_str <= deck["date"] <= max_date_str]
        found_decks = []

        for decklist in filtered_dataset:
            if player and player not in decklist["player"].lower():
                continue

            event = decklist['url'].split("-")[1]
            if event not in matchable_events:
                continue

            if self.__passes_whitelist_blacklist(search_in, decklist, whitelist, blacklist):
               found_decks.append(decklist)

        return found_decks

    def generate_decklist_report(self, decks: Optional[DATASET_CHUNK_TYPE]) -> str:
        """Format a list of decklists into a pretty-printable format with some additional metadata per card."""
        if not decks:
            return ""

        output = ""
        for deck in decks:
            output += f"\n {deck['player']} {deck['url']}"
            main = sorted(deck['main'].keys(), key=lambda k: self.card_metadata.data.get(k, {}).get('cmc', 0.0))
            side = sorted(deck['side'].keys(), key=lambda k: self.card_metadata.data.get(k, {}).get('cmc', 0.0))

            for card in main:
                mana_cost = self.card_metadata.data.get(card, {}).get("mana_cost", "{-}")
                output += f"\n{deck['main'][card]} {card} - {mana_cost}"
                
            output += "\n------ side ------"
            
            for card in side:
                mana_cost = self.card_metadata.data.get(card, {}).get("mana_cost", "{-}")
                output += f"\n{deck['side'][card]} {card} - {mana_cost}"
            
            output += "\n------ END OF DECK ------\n"
            
        return output

    def generate_card_frequency_report(self, sample: DATASET_CHUNK_TYPE, show_types: Optional[list[str]] = None) -> str:
        """Calculate the frequency of each card across the sample."""
        if not sample:
            return "No decks in sample"

        recognizeable_cards = self.card_metadata.data.keys()
        num_decks = len(sample)

        # Filter to instant, sorcery, etc.
        show_types = [string.capwords(t) for t in show_types] if show_types else []
        prevalence_dict = {"main": {}, "side": {}}
        max_card_len = 0
        unrecognizable_cards = set() 
        output = ""

        for location in config.SEARCH_IN_DEFAULT: # main and/or sideboard
            loc_dict = prevalence_dict[location]
            for deck in sample:
                for card, quantity in deck[location].items():
                    if card not in recognizeable_cards:
                        if card not in unrecognizable_cards:
                            unrecognizable_cards.add(card)
                            logger.warning(f"Unable to identify {card}. Please update card properties.")
                        continue
                    
                    if card in loc_dict:
                        loc_dict[card][0] += 1
                        loc_dict[card][1] += quantity
                    else:
                        loc_dict[card] = [1, quantity]
            
            if loc_dict:
                current_max = max(len(self.card_metadata.data.get(k, {}).get("display_name", str(k))) for k in loc_dict)
                max_card_len = max(max_card_len, current_max)

        if not prevalence_dict["main"] and not prevalence_dict["side"]:
            return "No recognizable cards found."

        max_quantity_len = len(str(max(prevalence_dict["main"].values(), key=lambda x: x[0], default=[0])[0]))            

        for location in config.SEARCH_IN_DEFAULT:
            if location == "side":
                output += "\n\n---SIDEBOARD---\n"

            if show_types:
                def keep(name: str) -> bool:
                    return any(t in self.card_metadata.data[name]["type"] for t in show_types)
                prevalence_dict[location] = {k: v for k, v in prevalence_dict[location].items() if keep(k)}

            quantity_descending = sorted(prevalence_dict[location].items(), key=lambda x: x[1][0], reverse=True)

            for card, quantity in quantity_descending:
                percentage = (quantity[0] / num_decks) * 100
                avg = quantity[1] / quantity[0]
                display_name = self.card_metadata.data.get(card, {}).get("display_name", str(card))
                output += (
                    f"\n{display_name:<{max_card_len}} | {quantity[0]:>{max_quantity_len}} decks | "
                    f"{percentage:>5.2f}% | {avg:.2f} avg"
                )

        return output

    def __passes_whitelist_blacklist(
            self, 
            search_in: list[str], 
            decklist: DeckEntry, 
            whitelist: list[str], 
            blacklist: list[str]
        ) -> bool:
        """Return whether a card meets all whitelist and blacklist criteria or not."""
        if not whitelist and not blacklist:
            return True
        
        left_to_match = len(whitelist)
        cards = "@".join(["@".join(decklist[location].keys()) for location in search_in])

        if any(b in cards for b in blacklist):
            return False
            
        for w in whitelist:
            if w in cards:
                if left_to_match <= 1:
                    return True
                left_to_match -= 1
                
        return False
