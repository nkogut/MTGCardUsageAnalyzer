import orjson as json
import matplotlib.pyplot as plt
import numpy
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
import numpy as np
from datetime import *
from typing import Union, Optional
import card_groups
import deck_analyzer as ca
import utils

def get_num_decks_by_month(considered_decks: ca.DATASET_CHUNK_TYPE,
                        dates: Optional[list[str]] = None) -> dict[str: int]:
    # Returns a dictionary with (k,v) = (month, total # of decks in considered_decks) for each month represented in considered_decks

    deck_dates = sorted([deck['date'][:7] for deck in considered_decks])
    if dates == None:
        start = deck_dates[0]
        end = deck_dates[-1]
        dates = utils.get_dates_between_months(start, end)

    num_decks = {date: 0 for date in dates}
    for date in dates:
        num_decks[date] = deck_dates.count(date)

    return num_decks


def get_card_frequency(card: str,
                  considered_decks: ca.DATASET_CHUNK_TYPE,
                  total_decks_per_month: dict[str: int],
                  search_in: list[str]) -> tuple[numpy.ndarray, numpy.ndarray]:
    # Returns the frequency of decks in the sample that include the given card

    start = min(considered_decks, key=lambda x: x['date'])['date'][:7]
    end = max(considered_decks, key=lambda x: x['date'])['date'][:7]
    dates = utils.get_dates_between_months(start, end)
    card_freq_dict = {date: 0 for date in dates}

    for deck in considered_decks:
        date = deck['date'][:7] # Exclude days
        if "main" in search_in and card in deck['main']:
            card_freq_dict[date] += 1
            continue

        if "side" in search_in and card in deck['side']:
            card_freq_dict[date] += 1

    card_freq_dict = {date: num for date, num in card_freq_dict.items() if num > 0} # Remove months not in sample

    # replace total # of cards with % of all decks
    for date, num_decks_playing in card_freq_dict.items():
        card_freq_dict[date] = num_decks_playing / total_decks_per_month[date]

    # Use datetime-based buckets for a cleaner  x-axis
    x = np.array([datetime(year=int(k[0:4]), day=1, month=int(k[5:7])) for k in card_freq_dict.keys()])
    y = np.array(list(card_freq_dict.values()))
    return x, y


def create_line_chart(considered_decks: ca.DATASET_CHUNK_TYPE,
                      cards: list[str] | None = None,
                      search_in: list[str] | None = None) -> None:
    # draws a chart of card frequency given the criteria for selecting decks

    if cards is None:
        cards = []
    cards = [card.split(" //")[0].lower() for card in cards]
    if search_in is None:
        search_in = ca.SEARCH_IN_DEFAULT

    fig, ax = plt.subplots()
    num_monthly_decks = get_num_decks_by_month(considered_decks)
    for card in cards:
        try:
            x, y = get_card_frequency(card, considered_decks, num_monthly_decks, search_in)
            x, y = zip(*sorted(zip(x, y)))
        except ValueError:
            pass

        plt.plot(x, y, label=card)

    plt.legend(loc='upper center')
    ax.yaxis.set_major_locator(MultipleLocator(.05))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    plt.grid(linewidth=.5, which='both')
    plt.show(block=False)

if __name__ == "__main__":
    # sample chart
    create_line_chart(cards=card_groups.MODERN_ARTIFACT_HATE,
                      considered_decks=ca.query_decks(dataset_path="Data/modern.json"))
