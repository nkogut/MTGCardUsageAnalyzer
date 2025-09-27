import orjson as json
import matplotlib.pyplot as plt
import numpy
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
import numpy as np
from datetime import *
from typing import Union, Optional
import card_groups
import card_analyzer as ca
import utils

def getNumDecksByMonth(consideredDecks: ca.DATASET_CHUNK_TYPE,
                        dates: Optional[list[str]] = None) -> dict[str: int]:
    # Returns a dictionary with (k,v) = (month, total # of decks in consideredDecks) for each month represented in consideredDecks

    deckDates = sorted([deck['date'][:7] for deck in consideredDecks])
    if dates == None:
        start = deckDates[0]
        end = deckDates[-1]
        dates = utils.getDatesBetweenMonths(start, end)

    numDecks = {date: 0 for date in dates}
    for date in dates:
        numDecks[date] = deckDates.count(date)

    return numDecks


def getCardFrequency(card: str,
                  consideredDecks: ca.DATASET_CHUNK_TYPE,
                  totalDecksPerMonth: dict[str: int],
                  searchIn: list[str]) -> tuple[numpy.ndarray, numpy.ndarray]:
    # Returns the frequency of decks in the sample that include the given card

    start = min(consideredDecks, key=lambda x: x['date'])['date'][:7]
    end = max(consideredDecks, key=lambda x: x['date'])['date'][:7]
    dates = utils.getDatesBetweenMonths(start, end)
    cardFreqDict = {date: 0 for date in dates}

    for deck in consideredDecks:
        date = deck['date'][:7] # Exclude days
        if "main" in searchIn and card in deck['main']:
            cardFreqDict[date] += 1
            continue

        if "side" in searchIn and card in deck['side']:
            cardFreqDict[date] += 1

    cardFreqDict = {date: num for date, num in cardFreqDict.items() if num > 0} # Remove months not in sample

    # replace total # of cards with % of all decks
    for date, numDecksPlaying in cardFreqDict.items():
        cardFreqDict[date] = numDecksPlaying / totalDecksPerMonth[date]

    # Use datetime-based buckets for a cleaner  x-axis
    x = np.array([datetime(year=int(k[0:4]), day=1, month=int(k[5:7])) for k in cardFreqDict.keys()])
    y = np.array(list(cardFreqDict.values()))
    return x, y


def createLineChart(consideredDecks: ca.DATASET_CHUNK_TYPE,
                      cards: list[str] | None = None,
                      searchIn: list[str] | None = None) -> None:
    # draws a chart of card frequency given the criteria for selecting decks

    if cards is None:
        cards = []
    cards = [card.split(" //")[0].lower() for card in cards]
    if searchIn is None:
        searchIn = ca.SEARCH_IN_DEFAULT

    fig, ax = plt.subplots()
    numMonthlyDecks = getNumDecksByMonth(consideredDecks)
    for card in cards:
        try:
            x, y = getCardFrequency(card, consideredDecks, numMonthlyDecks, searchIn)
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
    createLineChart(cards=card_groups.MODERN_ARTIFACT_HATE,
                      consideredDecks=ca.getDecks(dataset="Data/modern.json"))
