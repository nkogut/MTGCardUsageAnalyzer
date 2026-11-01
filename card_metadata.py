import gzip
import logging
import requests
import orjson as json
from unidecode import unidecode

import config

logger = logging.getLogger(__name__)

class CardMetadata:
    """Manages a JSON cache of Scryfall card metadata such as oracle text and CMC."""
    
    def __init__(self, force_update: bool = False):
        self.data = self._load_properties(force_update)

    def _load_properties(self, force: bool) -> dict:
        """Load the card properties from disk. Update if missing or forced."""
        if not config.CARD_PROPERTIES_PATH.is_file() or force:
            logger.info("Updating Card Properties dataset")
            self.update_dataset()

        return json.loads(config.CARD_PROPERTIES_PATH.read_bytes())

    def update_dataset(self) -> None: 
        """Call the Scryfall API to update the local cache of card metadata."""
        res = requests.get(config.SCRYFALL_BULK_DATA_URL, timeout=config.SCRYFALL_CATALOG_TIMEOUT)
        res.raise_for_status()
        
        bulk_dataset_link = res.text.split("Oracle Cards")[1].split('href="')[1].split('">')[0]

        res = requests.get(bulk_dataset_link, stream=True, timeout=config.SCRYFALL_BULK_DATA_TIMEOUT)
        res.raise_for_status()

        out = {}
        with gzip.GzipFile(fileobj=res.raw) as f:
            for line in f:
                c = json.loads(line)

                if c.get("set_type") in config.SCRYFALL_IGNORED_SET_TYPES or c.get("layout") in config.SCRYFALL_IGNORED_LAYOUTS:
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

        config.CARD_PROPERTIES_PATH.write_bytes(json.dumps(out))
        logger.info("Successfully updated card properties cache")
