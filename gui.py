import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter.filedialog import askopenfilename
from tkcalendar import DateEntry
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import Union
import card_analyzer as ca
import data_visualization as dv
import card_groups

DEFAULT_DATASET_FILE = "Data/sample_modern.json"
dataset = DEFAULT_DATASET_FILE

searchParams = {"whitelist": [], "blacklist": [], "player": None, "minDate": date(2000, 1, 1),
                      "maxDate": date(2100, 1, 1), "searchIn": ["main", "side"],
                      "eventType": ["league", "scheduled"]}

def chooseFile() -> None:
    global dataset
    dataset = askopenfilename()

def parseCommaSeparatedInput(input: str) -> list[str]:
    if input == "":
        return []
    input = input.title()
    out = input.split(", ")
    if len(out) > 1:
        return out
    else:
        return input.split(",")

def updateOutput(text: str) -> None:
    outputTextbox.config(state="normal")
    outputTextbox.delete(1.0, tk.END)
    outputTextbox.insert(1.0, text)
    outputTextbox.config(state="disabled")

def updateSearchParams() -> None:
    """
    Update query parameters with current gui state and use ca.getDecks() to get all relevant decks
    This is called by the "Analyze Decks", "Show Decks" and "Generate Chart" buttons, which pass it to other functions from CA to format it
    """
    # Set which part of deck to search in
    if not (searchSideboard.get() + searchMaindeck.get()) % 2 == 0:
        if searchMaindeck.get() == 0:
            searchParams["searchIn"] = ["side"]
        else:
            searchParams["searchIn"] = ["main"]
    else:
        searchParams["searchIn"] = ["main", "side"]

    # Set which types of events to search in
    if not (searchLeague.get() + searchScheduled.get()) % 2 == 0:
        if searchLeague.get() == 0:
            searchParams["eventType"] = ["scheduled"]
        else:
            searchParams["eventType"] = ["league"]
    else:
        searchParams["eventType"] = ["league", "scheduled"]

    # Set the date range
    minDate = minDateSelector.get_date()
    maxDate = maxDateSelector.get_date()
    if minDate > maxDate:
        updateOutput("End date is before start date")
        return
    searchParams["minDate"] = minDate
    searchParams["maxDate"] = maxDate

    # Set whitelist/blacklist
    searchParams["whitelist"] = parseCommaSeparatedInput(whitelistTextbox.get(1.0, "end-1c"))
    searchParams["blacklist"] = parseCommaSeparatedInput(blacklistTextbox.get(1.0, "end-1c"))

    # Set Player
    playerInput = playerTextbox.get(1.0, "end-1c")
    if playerInput == "":
        searchParams["player"] = None
    else:
        searchParams["player"] = playerInput

def generateChart() -> None:
    updateSearchParams()
    inputChart = parseCommaSeparatedInput(chartTextbox.get(1.0, "end-1c"))
    print(searchParams)
    if not inputChart:
        # Use dropdown
        dv.createLineChart(consideredDecks=ca.getDecks(dataset, *searchParams.values()),
                             eventType=searchParams["eventType"],
                             cards=card_groups.CARD_GROUP_DICT[chartDropdownValue.get()])
    else:
        # Use text input
        dv.createLineChart(consideredDecks=ca.getDecks(dataset, *searchParams.values()),
                             eventType=searchParams["eventType"],
                             cards=inputChart)


def queryDecks() -> list[dict[str, Union[str, dict[str, int]]]]:
    updateSearchParams()
    return ca.getDecks(dataset, *searchParams.values())

# Window setup
root = tk.Tk()
root.title("MTG Card Usage Analyzer")

# Dataset selection
filePickerButton = ttk.Button(root, text="Change Dataset", command=chooseFile)
analyzeDecksButton = ttk.Button(root, text="Analyze Decks", command=lambda: updateOutput(ca.getCardPrevalence(queryDecks())))
showDecksButton = ttk.Button(root, text="Show Decks", command=lambda: updateOutput(ca.displayDecks(queryDecks())))

# Maindeck/Sideboard selection
searchMaindeck = tk.IntVar(value=1)
searchSideboard = tk.IntVar(value=1)
searchInMenu = tk.Frame(root)
searchInMenuLabel = tk.Label(searchInMenu, text="Search in:")
searchInMaindeckCheckbox = ttk.Checkbutton(searchInMenu, text="Maindeck", variable=searchMaindeck)
searchInSideboardCheckbox = ttk.Checkbutton(searchInMenu, text="Sideboard", variable=searchSideboard)

searchInMenuLabel.grid(row=0, columnspan=2)
searchInMaindeckCheckbox.grid(row=1, column=0)
searchInSideboardCheckbox.grid(row=1, column=1)


#Event type selection
searchLeague = tk.IntVar(value=1)
searchScheduled = tk.IntVar(value=1)
eventTypeMenu = tk.Frame(root)
eventTypeMenuLabel = tk.Label(eventTypeMenu, text="Event types:")
leagueCheckbox = ttk.Checkbutton(eventTypeMenu, text="Leagues", variable=searchLeague)
scheduledCheckbox = ttk.Checkbutton(eventTypeMenu, text="Scheduled", variable=searchScheduled)

eventTypeMenuLabel.grid(row=0, columnspan=2)
leagueCheckbox.grid(row=1, column=0)
scheduledCheckbox.grid(row=1, column=1)


#Date selection
dateMenu = tk.Frame(root)
defaultStartDate = date.today() - relativedelta(months=6)
minDateLabel = tk.Label(dateMenu, text="Start date:")
maxDateLabel = tk.Label(dateMenu, text="End date:")
minDateSelector = DateEntry(dateMenu, year=defaultStartDate.year, month=defaultStartDate.month, day=1)
maxDateSelector = DateEntry(dateMenu)

minDateLabel.grid(row=0, column=0)
maxDateLabel.grid(row=0, column=1)
minDateSelector.grid(row=1, column=0)
maxDateSelector.grid(row=1, column=1)


# Whitelist/Blacklist selection
cardListInputMenu = tk.Frame(root)
whitelistLabel = tk.Label(cardListInputMenu, text="Decks including:")
blacklistLabel = tk.Label(cardListInputMenu, text="Excluding decks with:")
playerLabel = tk.Label(cardListInputMenu, text="Player (up to 1)")
cardListInputInstructionLabel = tk.Label(cardListInputMenu, text="Enter as 'card a,card b,card c'")
whitelistTextbox = tk.Text(cardListInputMenu, height=1, width=25)
blacklistTextbox = tk.Text(cardListInputMenu, height=1, width=25)
playerTextbox = tk.Text(cardListInputMenu, height=1, width=15)

cardListInputInstructionLabel.grid(row=0, column=1)
whitelistLabel.grid(row=1, column=0)
whitelistTextbox.grid(row=1, column=1)
blacklistLabel.grid(row=2, column=0)
blacklistTextbox.grid(row=2, column=1)
playerLabel.grid(row=3, column=0)
playerTextbox.grid(row=3, column=1)


# Chart selection
chartMenu = tk.Frame(root)
generateChartButton = ttk.Button(chartMenu, text="Generate Historical Graph", command=generateChart)
customChartLabel = tk.Label(chartMenu, text="Optional - Graph the prevalence of these cards:")
presetChartLabel = tk.Label(chartMenu, text="Or choose a preset group")
chartDropdownValue = tk.StringVar()
chartDropdownValue.set(list(card_groups.CARD_GROUP_DICT.keys())[0])
chartDropdown = tk.OptionMenu(chartMenu, chartDropdownValue, *card_groups.CARD_GROUP_DICT.keys())
chartTextbox = tk.Text(chartMenu, height=1, width=25)

customChartLabel.grid(row=0, column=0)
chartTextbox.grid(row=0, column=1)
generateChartButton.grid(row=0, column=2)
presetChartLabel.grid(row=1, column=0)
chartDropdown.grid(row=1, column=1)


# Output
outputTextbox = scrolledtext.ScrolledText(root, state="disabled", width=80, height=10, wrap=tk.WORD)


# Populate window
filePickerButton.grid(row=0, column=0)
dateMenu.grid(row=0, column=1)
searchInMenu.grid(row=1, column=0)
eventTypeMenu.grid(row=1, column=1)
cardListInputMenu.grid(row=2, columnspan=2)
analyzeDecksButton.grid(row=3, column=0)
showDecksButton.grid(row=3, column=1)
chartMenu.grid(row=4, columnspan=2)
outputTextbox.grid(row=6, columnspan=2)


# Draw window
mainframe = ttk.Frame(root)
root.mainloop()
