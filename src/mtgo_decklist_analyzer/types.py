from collections import defaultdict
from datetime import date
from typing import TypedDict

CardCounts = dict[str, int]
MonthlyDeckCounts = dict[str, int]
FreqCounter = dict[str, defaultdict[str, list[int]]]

class ScryfallCard(TypedDict):
    """Schema for cached card properties."""

    display_name: str
    type: str
    uri: str
    mana_cost: str
    cmc: float
    oracle: str

class DeckEntry(TypedDict):
    """JSON schema for one full tournament deck."""

    date: str
    player: str
    url: str
    main: dict[str, int]
    side: dict[str, int]

DeckEntries = list[DeckEntry]

class SearchParams(TypedDict):
    """Decklist filter criteria schema."""

    whitelist: list[str]
    blacklist: list[str]
    player: str | None
    min_date: date
    max_date: date
    search_in: list[str]
    event_types: list[str]

class UnsuccessfulUrls(TypedDict):
    """Schema for URLs that have been accessed. These URLs may be discarded or retried."""

    # May be retried
    listing: list[str]
    event: list[str]

    # May not be retried
    discarded: list[str]

class StoredUrls(TypedDict):
    """Schema for all accessed URLs for a dataset."""

    complete: list[str]
    incomplete: UnsuccessfulUrls
