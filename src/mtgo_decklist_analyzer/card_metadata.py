import gzip
import logging

import orjson as json
import requests
from unidecode import unidecode

from mtgo_decklist_analyzer.config import SETTINGS
from mtgo_decklist_analyzer.types import ScryfallCard

logger = logging.getLogger(__name__)

class CardMetadata:
    """Manages a JSON cache of Scryfall card metadata such as oracle text and CMC."""

    def __init__(self, force_update: bool = False) -> None:
        self.data = self._load_properties(force_update)

    def _load_properties(self, force: bool) -> dict[str, ScryfallCard]:
        """Load the card properties from disk. Update if missing or forced."""
        if not SETTINGS.paths.card_properties.is_file() or force:
            logger.info("Updating Card Properties dataset")
            self.update_dataset()

        return json.loads(SETTINGS.paths.card_properties.read_bytes())

    def update_dataset(self) -> None:
        """Call the Scryfall API to update the local cache of card metadata."""
        res = requests.get(SETTINGS.scryfall.bulk_data_url, timeout=SETTINGS.scryfall.catalog_timeout)
        res.raise_for_status()

        bulk_dataset_link = res.text.split("Oracle Cards")[1].split('href="')[1].split('">')[0]
        res = requests.get(bulk_dataset_link, stream=True, timeout=SETTINGS.scryfall.bulk_timeout)
        res.raise_for_status()

        out: dict[str, ScryfallCard] = {}

        with gzip.GzipFile(fileobj=res.raw) as f:
            for line in f:
                c = json.loads(line)

                if (
                    c.get("set_type") in SETTINGS.scryfall.ignored_set_categories # e.g. Vanguard
                    or c.get("layout") in SETTINGS.scryfall.ignored_card_layouts # e.g. Plane
                ):
                    continue

                name = c["name"]
                lower_name = unidecode(name).lower().split(" //")[0]

                if faces := c.get("card_faces"):
                    front, back = faces[0], faces[1]
                    if back.get("mana_cost"):
                        mana_cost = f"{front.get('mana_cost', '')} // {back['mana_cost']}"
                    else:
                        mana_cost = front.get("mana_cost", "")
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

        SETTINGS.paths.card_properties.write_bytes(json.dumps(out))
        logger.info("Successfully updated card properties cache")

    def resolve_card_name(self, partial_name: str) -> str:
        """Find the closest 'autocomplete' match for a card name."""
        partial = partial_name.lower()
        if partial in self.data:
            logger.debug(f"Resolved {partial_name} without changes")
            return partial

        if matches := [c for c in self.data if partial in c]:
            match = min(matches, key=len)
            logger.debug(f"Resolved {partial_name} to {match}")
            return match

        return partial_name
