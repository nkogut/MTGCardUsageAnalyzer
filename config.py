from datetime import date
from pathlib import Path
from typing import TypedDict

import pandas as pd

# Daily Aggregates
AGG_START_DATE = pd.Timestamp("2022-12-01")
AGG_PLAY_RATE_PATH = Path("aggregate_data/playrates.parquet")

# Data Paths
DATA_DIR = Path("Data")
CARD_PROPERTIES_PATH = DATA_DIR / "card_properties.json"
URLS_FILE_SUFFIX = "_urls.json"
JSON_EXT = ".json"
XML_EXT = ".xml"
MODERN_DATA_PATH = DATA_DIR / "modern.json"

# Dates
DEFAULT_MIN_DATE = date(1900, 1, 1)
DEFAULT_MAX_DATE = date(2100, 1, 1)
DEFAULT_MIN_DATE_STR = "1900/01"
DEFAULT_MAX_DATE_STR = "9999/01"
DATE_FMT_DECK = "%Y-%m-%d"
DATE_FMT_CLI = "%Y/%m"

# ==== Scryfall ====
SCRYFALL_BULK_DATA_URL = "https://scryfall.com/docs/api/bulk-data"
SCRYFALL_IGNORED_SET_TYPES = frozenset(["vanguard", "token", "memorabilia", "alchemy", "minigame"])
SCRYFALL_IGNORED_LAYOUTS = frozenset(["art_series", "planar", "scheme"])
SCRYFALL_CATALOG_TIMEOUT = 10
SCRYFALL_BULK_DATA_TIMEOUT = 30

CARD_TYPE_SEPARATORS = (
    "Creature (", "Land (", "Instant (", "Sorcery (", "Artifact (", "Enchantment (", "Planeswalker (","Other (",
    "Rarity", "Cards"
)

MTGO_DECKLIST_PREFIX = "https://www.mtgo.com/decklist/"
MTGO_DECKLISTS_LIST_PREFIX = "https://www.mtgo.com/decklists/"
DECK_START_INDEX = 9

# Default settings
DRIVER_TIMEOUT = 4
DEFAULT_GRACE_DAYS = 7

# ==== Analyzer ====
class DeckEntry(TypedDict):
    """JSON stored representation of one deck within a tournamnet."""

    date: str
    player: str
    url: str
    main: dict[str, int]
    side: dict[str, int]

DATASET_CHUNK_TYPE = list[DeckEntry]

# Default settings
EVENT_TYPES = {
    "league": ["league", "gold", "daily"],
    "scheduled": ["prelim", "challenge", "ptq", "championship", "qualifier", "playoff", "finals", "last-chance"]
}
DEFAULT_EVENT_TYPES = ("league", "scheduled")
SEARCH_IN_DEFAULT = frozenset(["main", "side"])



