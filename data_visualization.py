import json
import matplotlib.pyplot as plt
import numpy
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
import numpy as np
from datetime import *
from typing import Union, Optional

import card_groups
import card_groups as groups
import card_analyzer as ca

def total_monthly_decks(month: str,
                        event_type: list[str],
                        decks_considered: ca.DATASET_CHUNK_TYPE):
    # returns the number of decks in a given month

    total = 0
    for deck in decks_considered:
        if not deck['url'].split("-")[1] in event_type:
            continue
        if deck['date'][:7] == month:
            total += 1
    return total

def find_ind_freq(card: str,
                  event_type: list[str],
                  decks_considered: ca.DATASET_CHUNK_TYPE,
                  search_in: list[str]) -> tuple[numpy.ndarray, numpy.ndarray]:
    # Returns the frequency of decks in the sample that include the given card

    freq_card_dict: dict[str, int] = {}
    for deck in decks_considered:
        found = False
        if not deck['url'].split("-")[1] in event_type:
            continue
        if "maindeck" in search_in:
            for k in deck['maindeck'].keys():
                if card == k:
                    found = True
                    if deck['date'][:7] in freq_card_dict.keys():
                        # only include month/year to display with monthly buckets
                        freq_card_dict[deck['date'][:7]] = freq_card_dict[deck['date'][:7]] + 1
                    else:
                        freq_card_dict[deck['date'][:7]] = 1

        if not found and "sideboard" in search_in:
            for k in deck['sideboard'].keys():
                if card == k:
                    if deck['date'][:7] in freq_card_dict.keys():
                        # only include month/year to display with monthly buckets
                        freq_card_dict[deck['date'][:7]] = freq_card_dict[deck['date'][:7]] + 1
                    else:
                        freq_card_dict[deck['date'][:7]] = 1

    # replace total # of cards with % of all decks
    for k, v in freq_card_dict.items():
        freq_card_dict[k] = v/total_monthly_decks(k, event_type=event_type, decks_considered=decks_considered)

    # Use datetime-based buckets for a cleaner  x-axis
    x = np.array([datetime(year=int(k[0:4]), day=1, month=int(k[5:7])) for k in freq_card_dict.keys()])
    y = np.array(list(freq_card_dict.values()))
    return x, y

def create_line_chart(decks_considered: ca.DATASET_CHUNK_TYPE,
                      event_type: list[str] | None = None,
                      cards: list[str] | None = None,
                      search_in: list[str] | None = None) -> None:
    # draws a chart of card frequency given the criteria for selecting decks

    # set default values for lists if none are supplied
    if cards is None:
        cards = []
    if event_type is None:
        event_type = ["preliminary", "challenge", "showcase", "last", "qualifier"]
    if search_in is None:
        search_in = ["maindeck", "sideboard"]

    fig, ax = plt.subplots()
    for c in cards:
        try:
            x, y = find_ind_freq(card=c, event_type=event_type, decks_considered=decks_considered, search_in=search_in)
            x, y = zip(*sorted(zip(x, y)))
        except ValueError:
            pass

        plt.plot(x, y, label=c)

    plt.legend(loc='upper center')
    ax.yaxis.set_major_locator(MultipleLocator(.05))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    plt.grid(linewidth=.5, which='both')
    plt.show()

if __name__ == "__main__":
    # sample chart
    # create_line_chart(event_type=["league"],
    #                   cards=card_groups.MODERN_METAGAME_5_2024,
    #                   decks_considered=ca.find_decks(dataset=ca.load_dataset("Data/full_modern.json"), min_date=date(2022, 1, 1)))
    
    create_line_chart(cards=card_groups.MODERN_ARTIFACT_HATE,
                      decks_considered=ca.find_decks(dataset=ca.load_dataset("Data/Modern.json"), min_date=date(2025, 1, 1)))

