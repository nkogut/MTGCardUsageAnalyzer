import json
import logging
from datetime import datetime
from pathlib import Path

from mtgo_decklist_analyzer import _deck_sax
from mtgo_decklist_analyzer.card_metadata import CardMetadata
from mtgo_decklist_analyzer.types import DeckEntries, SearchParams

logger = logging.getLogger(__name__)

class DeckAnalyzer:
    """Analyzes card pairing and deck construction data for a particular metagame."""

    def __init__(self, dataset_path: Path, card_metadata: CardMetadata) -> None:
        self.dataset_path = dataset_path
        self.card_metadata = card_metadata
        self._last_freq_report = ""

    def query_decks(self, params: SearchParams | None = None, return_decks: bool = False) -> DeckEntries:
        """Gather all decks matching the specified criteria by calling the SAX parser."""
        if params is None:
            return []

        start_ts = max(0, int((params["min_date"] - datetime(1970, 1, 1).date()).total_seconds()))
        end_ts = max(0, int((params["max_date"] - datetime(1970, 1, 1).date()).total_seconds()))

        player_str = params.get("player") or ""
        whitelist = params.get("whitelist", [])
        blacklist = params.get("blacklist", [])

        # Parse data in C++ and build the frequency string
        # Only serialize the decks back to Python objects if it is needed downstream by setting return_decks=True
        json_bytes, freq_str = _deck_sax.analyze_metagame(
            str(self.dataset_path),
            start_ts,
            end_ts,
            player_str,
            whitelist,
            blacklist,
            return_decks
        )

        self._last_freq_report = freq_str

        if not return_decks:
            return [] # Dummy return value to prevent further downstream processing

        return json.loads(json_bytes)

    def generate_decklist_report(self, decks: DeckEntries | None) -> str:
        """Format a list of decklists into a pretty-printable format with some additional metadata per card."""
        if not decks or decks == [1]:
            return "No decks provided to generator (or return_decks was False)."

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

    def generate_card_frequency_report(self) -> str:
        """Return the frequency of each card across the sample.

        Frequencies are calculated during parsing and stored for future reference.
        """
        return self._last_freq_report
