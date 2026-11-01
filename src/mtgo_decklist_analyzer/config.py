import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

@dataclass(frozen=True)
class DataPaths:
    """Dataset-related paths."""

    data_dir: Path
    modern_data: Path
    card_properties: Path
    agg_play_rate: Path

@dataclass(frozen=True)
class Extensions:
    """File extension constants."""

    urls_file_suffix: str
    json: str
    xml: str

@dataclass(frozen=True)
class DatesConfig:
    """Date boundaries and formatting constants."""

    agg_start_date: pd.Timestamp
    default_min_date: date
    default_max_date: date
    default_min_date_str: str
    default_max_date_str: str
    date_fmt_deck: str
    date_fmt_cli: str

@dataclass(frozen=True)
class ScryfallSettings:
    """Scryfall API config."""

    bulk_data_url: str
    ignored_set_categories: frozenset[str]
    ignored_card_layouts: frozenset[str]
    catalog_timeout: int
    bulk_timeout: int

@dataclass(frozen=True)
class ScraperSettings:
    """MTGO decklist web scraper configuration."""

    mtgo_decklist_prefix: str
    mtgo_decklists_list_prefix: str
    deck_start_index: int
    driver_timeout: int
    default_grace_days: int
    card_type_separators: tuple[str, ...]

@dataclass(frozen=True)
class AnalyzerSettings:
    """Decklist filtering and search defaults."""

    default_event_types: tuple[str, ...]
    search_in_default: frozenset[str]
    event_types: dict[str, list[str]]

@dataclass(frozen=True)
class AppConfig:
    """Overall configuration schema."""

    paths: DataPaths
    extensions: Extensions
    dates: DatesConfig
    scryfall: ScryfallSettings
    scraper: ScraperSettings
    analyzer: AnalyzerSettings

def _load_settings() -> AppConfig:
    raw = tomllib.loads((ROOT_DIR / "config.toml").read_text(encoding="utf-8"))

    return AppConfig(
        paths=DataPaths(
            data_dir=Path(raw["paths"]["data_dir"]),
            modern_data=Path(raw["paths"]["modern_data"]),
            card_properties=Path(raw["paths"]["card_properties"]),
            agg_play_rate=Path(raw["paths"]["agg_play_rate"])
        ),
        extensions=Extensions(
            urls_file_suffix=raw["extensions"]["urls_file_suffix"],
            json=raw["extensions"]["json"],
            xml=raw["extensions"]["xml"]
        ),
        dates=DatesConfig(
            agg_start_date=pd.Timestamp(raw["dates"]["agg_start_date"]),
            default_min_date=date.fromisoformat(raw["dates"]["default_min_date"]),
            default_max_date=date.fromisoformat(raw["dates"]["default_max_date"]),
            default_min_date_str=raw["dates"]["default_min_date_str"],
            default_max_date_str=raw["dates"]["default_max_date_str"],
            date_fmt_deck=raw["dates"]["date_fmt_deck"],
            date_fmt_cli=raw["dates"]["date_fmt_cli"]
        ),
        scryfall=ScryfallSettings(
            bulk_data_url=raw["scryfall"]["bulk_data_url"],
            ignored_set_categories=frozenset(raw["scryfall"]["ignored_set_categories"]),
            ignored_card_layouts=frozenset(raw["scryfall"]["ignored_card_layouts"]),
            catalog_timeout=raw["scryfall"]["catalog_timeout"],
            bulk_timeout=raw["scryfall"]["bulk_data_timeout"]
        ),
        scraper=ScraperSettings(
            mtgo_decklist_prefix=raw["scraper"]["mtgo_decklist_prefix"],
            mtgo_decklists_list_prefix=raw["scraper"]["mtgo_decklists_list_prefix"],
            deck_start_index=raw["scraper"]["deck_start_index"],
            driver_timeout=raw["scraper"]["driver_timeout"],
            default_grace_days=raw["scraper"]["default_grace_days"],
            card_type_separators=tuple(raw["scraper"]["card_type_separators"])
        ),
        analyzer=AnalyzerSettings(
            default_event_types=tuple(raw["analyzer"]["default_event_types"]),
            search_in_default=frozenset(raw["analyzer"]["search_in_default"]),
            event_types=raw["analyzer"]["event_types"]
        )
    )

SETTINGS = _load_settings()
CARD_GROUPS = tomllib.loads((ROOT_DIR / "card_groups.toml").read_text(encoding="utf-8"))
