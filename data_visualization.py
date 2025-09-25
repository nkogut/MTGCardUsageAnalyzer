import orjson as json
import matplotlib.pyplot as plt
import numpy
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
import numpy as np
from datetime import *
from typing import Union, Optional

import card_groups
import card_analyzer as ca

def numMonthlyDecks(month: str,
                        eventType: list[str],
                        consideredDecks: ca.DATASET_CHUNK_TYPE):
    # returns the number of decks in a given month

    total = 0
    for deck in consideredDecks:
        if not deck['url'].split("-")[1] in eventType:
            continue
        if deck['date'][:7] == month:
            total += 1
    return total

def getCardFrequency(card: str,
                  eventType: list[str],
                  consideredDecks: ca.DATASET_CHUNK_TYPE,
                  searchIn: list[str]) -> tuple[numpy.ndarray, numpy.ndarray]:
    # Returns the frequency of decks in the sample that include the given card

    cardFreqDict: dict[str, int] = {}
    for deck in consideredDecks:
        found = False
        if not deck['url'].split("-")[1] in eventType:
            continue
        if "main" in searchIn:
            for k in deck['main'].keys():
                if card == k:
                    found = True
                    if deck['date'][:7] in cardFreqDict.keys():
                        # only include month/year to display with monthly buckets
                        cardFreqDict[deck['date'][:7]] = cardFreqDict[deck['date'][:7]] + 1
                    else:
                        cardFreqDict[deck['date'][:7]] = 1

        if not found and "side" in searchIn:
            for k in deck['side'].keys():
                if card == k:
                    if deck['date'][:7] in cardFreqDict.keys():
                        # only include month/year to display with monthly buckets
                        cardFreqDict[deck['date'][:7]] = cardFreqDict[deck['date'][:7]] + 1
                    else:
                        cardFreqDict[deck['date'][:7]] = 1

    # replace total # of cards with % of all decks
    for k, v in cardFreqDict.items():
        cardFreqDict[k] = v/numMonthlyDecks(k, eventType=eventType, consideredDecks=consideredDecks)

    # Use datetime-based buckets for a cleaner  x-axis
    x = np.array([datetime(year=int(k[0:4]), day=1, month=int(k[5:7])) for k in cardFreqDict.keys()])
    y = np.array(list(cardFreqDict.values()))
    return x, y

def createLineChart(consideredDecks: ca.DATASET_CHUNK_TYPE,
                      eventType: list[str] | None = None,
                      cards: list[str] | None = None,
                      searchIn: list[str] | None = None) -> None:
    # draws a chart of card frequency given the criteria for selecting decks

    # set default values for lists if none are supplied
    if cards is None:
        cards = []
    if eventType is None:
        eventType = ["preliminary", "challenge", "showcase", "last", "qualifier"]
    if searchIn is None:
        searchIn = ["main", "side"]

    fig, ax = plt.subplots()
    for c in cards:
        try:
            x, y = getCardFrequency(card=c, eventType=eventType, consideredDecks=consideredDecks, searchIn=searchIn)
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
    createLineChart(cards=card_groups.MODERN_ARTIFACT_HATE,
                      consideredDecks=ca.getDecks(dataset=ca.loadDataset("Data/Modern.json"), minDate=date(2025, 1, 1)))
