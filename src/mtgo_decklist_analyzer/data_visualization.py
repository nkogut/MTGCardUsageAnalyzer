from collections import Counter
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator, MultipleLocator

from mtgo_decklist_analyzer.card_metadata import CardMetadata
from mtgo_decklist_analyzer.config import CARD_GROUPS, SETTINGS
from mtgo_decklist_analyzer.deck_analyzer import DeckAnalyzer
from mtgo_decklist_analyzer.types import DeckEntries


def get_card_frequency(card: str, considered_decks: DeckEntries, search_in: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Calculate the frequency of a card within the sample period."""
    total_decks, card_decks = Counter(), Counter()

    for deck in considered_decks:
        total_decks[month := datetime.fromtimestamp(deck["date"]).strftime(SETTINGS.dates.date_fmt_cli)] += 1
        if ("main" in search_in and card in deck["main"]) or ("side" in search_in and card in deck["side"]):
            card_decks[month] += 1

    months = sorted(m for m, count in card_decks.items() if count > 0 and total_decks[m] > 0)

    x = np.array([datetime(int(m[:4]), int(m[5:7]), 1) for m in months])
    y = np.array([card_decks[m] / total_decks[m] for m in months])

    return x, y


def create_line_chart(
        considered_decks: DeckEntries,
        cards: list[str] | None = None,
        search_in: list[str] | None = None
    ) -> None:
    """Draw a card frequency chart for the selected decks."""
    cards = [c.split(" //")[0].lower() for c in (cards or [])]
    search_in = search_in or list(SETTINGS.analyzer.search_in_default)

    _fig, ax = plt.subplots()

    for card in cards:
        x, y = get_card_frequency(card, considered_decks, search_in)
        if not len(x):
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
