import pandas as pd
from datetime import date
from pathlib import Path

# Daily Aggregates
AGG_START_DATE = pd.Timestamp("2022-12-01")
AGG_PLAY_RATE_PATH = "goat/playrates.parquet"

# Data Paths
DATA_DIR = Path("Data")
CARD_PROPERTIES_PATH = DATA_DIR / "card_properties.json"
URLS_FILE_SUFFIX = "_urls.json"
JSON_EXT = ".json"
XML_EXT = ".xml"

# Dates
DEFAULT_MIN_DATE = date(1900, 1, 1)
DEFAULT_MAX_DATE = date(2100, 1, 1)
DEFAULT_MIN_DATE_STR = "1900/01"
DEFAULT_MAX_DATE_STR = "9999/01"
DATE_FMT_DECK = "%Y-%m-%d"
DATE_FMT_CLI = "%Y/%m"

# ==== Scraper ====
SCRYFALL_BULK_DATA_URL = "https://scryfall.com/docs/api/bulk-data"
SCRYFALL_IGNORED_SET_TYPES = frozenset(["vanguard", "token", "memorabilia", "alchemy", "minigame"])
SCRYFALL_IGNORED_LAYOUTS = frozenset(["art_series", "planar", "scheme"])

CARD_TYPE_SEPARATORS = (
    "Creature (", "Land (", "Instant (", "Sorcery (", "Artifact (", "Enchantment (", "Planeswalker (","Other (", 
    "Rarity", "Cards"
)

MTGO_DECKLIST_PREFIX = "https://www.mtgo.com/decklist/"
MTGO_DECKLISTS_LIST_PREFIX = "https://www.mtgo.com/decklists/"

# Default settings
SCRAPER_DRIVER_TIMEOUT = 4
DEFAULT_GRACE_DAYS = 7

# ==== Analyzer ====

# Default settings
EVENT_TYPES = {
    "league": ["league", "gold", "daily"],
    "scheduled": ["prelim", "challenge", "ptq", "championship", "qualifier", "playoff", "finals", "last-chance"]
}
DEFAULT_EVENT_TYPES = ("league", "scheduled")
SEARCH_IN_DEFAULT = frozenset(["main", "side"])



