from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator, MultipleLocator

from mtgo_decklist_analyzer import utils
from mtgo_decklist_analyzer.card_metadata import CardMetadata
from mtgo_decklist_analyzer.config import CARD_GROUPS, SETTINGS
from mtgo_decklist_analyzer.deck_analyzer import DeckAnalyzer
from mtgo_decklist_analyzer.types import DeckEntries


def get_num_decks_by_month(
        considered_decks: DeckEntries,
        dates: list[str] | None = None
    ) -> dict[str, int]:
    """Return {month: total # of decks in considered_decks that month}."""
    deck_dates = sorted([deck['date'][:7] for deck in considered_decks])
    if dates is None:
        start = deck_dates[0]
        end = deck_dates[-1]
        dates = utils.get_dates_between_months(start, end)

    num_decks = dict.fromkeys(dates, 0)
    for date in dates:
        num_decks[date] = deck_dates.count(date)

    return num_decks


def get_card_frequency(
        card: str,
        considered_decks: DeckEntries,
        total_decks_per_month: dict[str, int],
        search_in: list[str]
    ) -> tuple[np.ndarray, np.ndarray]:
    """Calculate the frequency of card within the sample period."""
    start = min(considered_decks, key=lambda x: x['date'])['date'][:7]
    end = max(considered_decks, key=lambda x: x['date'])['date'][:7]
    dates = utils.get_dates_between_months(start, end)
    card_freqs = dict.fromkeys(dates, 0)

    for deck in considered_decks:
        date = deck['date'][:7].replace("-", "/") # Ignore days
        if "main" in search_in and card in deck['main']:
            card_freqs[date] += 1
            continue

        if "side" in search_in and card in deck['side']:
            card_freqs[date] += 1

    card_freqs = {
        date: num / total_decks_per_month[date]
        for date, num in card_freqs.items()
        if num > 0 and total_decks_per_month[date] > 0
    }

    # Use datetime-based buckets for a cleaner  x-axis
    x = np.array([datetime(year=int(k[0:4]), day=1, month=int(k[5:7])) for k in card_freqs])
    y = np.array(list(card_freqs.values()))
    return x, y


def create_line_chart(
        considered_decks: DeckEntries,
        cards: list[str] | None = None,
        search_in: list[str] | None = None
    ) -> None:
    """Draw a card frequency chart for the selected decks."""
    if cards is None:
        cards = []
    cards = [card.split(" //")[0].lower() for card in cards]
    if search_in is None:
        search_in = list(SETTINGS.analyzer.search_in_default)

    _fig, ax = plt.subplots()
    num_monthly_decks = get_num_decks_by_month(considered_decks)
    for card in cards:
        try:
            x, y = get_card_frequency(card, considered_decks, num_monthly_decks, search_in)
            x, y = zip(*sorted(zip(x, y, strict=True)), strict=True)
        except ValueError:
            continue

        plt.plot(x, y, label=card)

    plt.legend(loc='upper center')
    ax.yaxis.set_major_locator(MultipleLocator(.05))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    plt.grid(linewidth=.5, which='both')
    plt.show(block=False)

if __name__ == "__main__":
    # sample chart
    metadata = CardMetadata()
    analyzer = DeckAnalyzer(dataset_path=SETTINGS.paths.modern_data, card_metadata=metadata)

    create_line_chart(
        cards=CARD_GROUPS["modern"]["artifact_hate"],
        considered_decks=analyzer.query_decks()
    )
