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

DEFAULT_DATASET_FILE = "Data/2024_Decks.json"

dataset_file = DEFAULT_DATASET_FILE
dataset = ca.load_dataset(dataset_file)

deck_search_params = {"whitelist": [], "blacklist": [], "player": None, "min_date": date(2000, 1, 1),
                      "max_date": date(2100, 1, 1), "search_in": ["maindeck", "sideboard"],
                      "event_type": ["league", "scheduled"]}

def choose_file() -> None:
    dataset_file = askopenfilename()
    dataset = ca.load_dataset(dataset_file)

def comma_separated_input_parser(input: str) -> list[str]:
    if input == "":
        return []
    input = input.title()
    out = input.split(", ")
    if len(out) > 1:
        return out
    else:
        return input.split(",")

def update_output(text: str) -> None:
    output_textbox.config(state="normal")
    output_textbox.delete(1.0, tk.END)
    output_textbox.insert(1.0, text)
    output_textbox.config(state="disabled")

def update_deck_search_params() -> None:
    """
    Update query parameters with current gui state and use ca.find_decks() to get all relevant decks
    This is called by the "Analyze Decks", "Show Decks" and "Generate Chart" buttons, which pass it to other functions from CA to format it
    """
    # Set which part of deck to search in
    if not (search_sideboard.get() + search_maindeck.get()) % 2 == 0:
        if search_maindeck.get() == 0:
            deck_search_params["search_in"] = ["sideboard"]
        else:
            deck_search_params["search_in"] = ["maindeck"]
    else:
        deck_search_params["search_in"] = ["maindeck", "sideboard"]

    # Set which types of events to search in
    if not (search_league.get() + search_scheduled.get()) % 2 == 0:
        if search_league.get() == 0:
            deck_search_params["event_type"] = ["scheduled"]
        else:
            deck_search_params["event_type"] = ["league"]
    else:
        deck_search_params["event_type"] = ["league", "scheduled"]

    # Set the date range
    min_date = min_date_selector.get_date()
    max_date = max_date_selector.get_date()
    if min_date > max_date:
        update_output("End date is before start date")
        return
    deck_search_params["min_date"] = min_date
    deck_search_params["max_date"] = max_date

    # Set whitelist/blacklist
    deck_search_params["whitelist"] = comma_separated_input_parser(whitelist_textbox.get(1.0, "end-1c"))
    deck_search_params["blacklist"] = comma_separated_input_parser(blacklist_textbox.get(1.0, "end-1c"))

    # Set Player
    player_input = player_textbox.get(1.0, "end-1c")
    if player_input == "":
        deck_search_params["player"] = None
    else:
        deck_search_params["player"] = player_input

def generate_chart() -> None:
    update_deck_search_params()
    input_chart_cards = comma_separated_input_parser(chart_cards_textbox.get(1.0, "end-1c"))
    if not input_chart_cards:
        # Use dropdown
        dv.create_line_chart(event_type=deck_search_params["event_type"],
                             cards=card_groups.CARD_GROUP_DICT[chart_dropdown.get()],
                             decks_considered=ca.find_decks(dataset, *deck_search_params.values()))
    else:
        # Use text input
        dv.create_line_chart(event_type=deck_search_params["event_type"],
                             cards=input_chart_cards,
                             decks_considered=ca.find_decks(dataset, *deck_search_params.values()))

def query_decks() -> list[dict[str, Union[str, dict[str, int]]]]:
    update_deck_search_params()
    return ca.find_decks(dataset, *deck_search_params.values())

# Window setup
root = tk.Tk()
root.title("MTG Card Usage Analyzer")

# Dataset selection
file_picker_button = ttk.Button(root, text="Change Dataset", command=choose_file)
analyze_decks_button = ttk.Button(root, text="Analyze Decks", command=lambda: update_output(ca.find_card_prevalence(query_decks())))
show_decks_button = ttk.Button(root, text="Show Decks", command=lambda: update_output(ca.display_decks(query_decks())))

# Maindeck/Sideboard selection
search_maindeck = tk.IntVar(value=1)
search_sideboard = tk.IntVar(value=1)
deck_location_menu = tk.Frame(root)
deck_location_label = tk.Label(deck_location_menu, text="Search in:")
maindeck_checkbox = ttk.Checkbutton(deck_location_menu, text="Maindeck", variable=search_maindeck)
sideboard_checkbox = ttk.Checkbutton(deck_location_menu, text="Sideboard", variable=search_sideboard)

deck_location_label.grid(row=0, columnspan=2)
maindeck_checkbox.grid(row=1, column=0)
sideboard_checkbox.grid(row=1, column=1)


#Event type selection
search_league = tk.IntVar(value=1)
search_scheduled = tk.IntVar(value=1)
event_type_menu = tk.Frame(root)
event_type_label = tk.Label(event_type_menu, text="Event types:")
league_checkbox = ttk.Checkbutton(event_type_menu, text="Leagues", variable=search_league)
scheduled_checkbox = ttk.Checkbutton(event_type_menu, text="Scheduled", variable=search_scheduled)

event_type_label.grid(row=0, columnspan=2)
league_checkbox.grid(row=1, column=0)
scheduled_checkbox.grid(row=1, column=1)


#Date selection
date_menu = tk.Frame(root)
default_start_date = date.today() + relativedelta(months=-6)
min_date_label = tk.Label(date_menu, text="Start date:")
max_date_label = tk.Label(date_menu, text="End date:")
min_date_selector = DateEntry(date_menu, year=default_start_date.year, month=default_start_date.month, day=1)
max_date_selector = DateEntry(date_menu)

min_date_label.grid(row=0, column=0)
max_date_label.grid(row=0, column=1)
min_date_selector.grid(row=1, column=0)
max_date_selector.grid(row=1, column=1)


# Whitelist/Blacklist selection
text_input_menu = tk.Frame(root)
whitelist_label = tk.Label(text_input_menu, text="Decks including:")
blacklist_label = tk.Label(text_input_menu, text="Excluding decks with:")
player_label = tk.Label(text_input_menu, text="Player (up to 1)")
whitelist_instruction_label = tk.Label(text_input_menu, text="Enter as 'card a,card b,card c'")
whitelist_textbox = tk.Text(text_input_menu, height=1, width=25)
blacklist_textbox = tk.Text(text_input_menu, height=1, width=25)
player_textbox = tk.Text(text_input_menu, height=1, width=15)

whitelist_instruction_label.grid(row=0, column=1)
whitelist_label.grid(row=1, column=0)
whitelist_textbox.grid(row=1, column=1)
blacklist_label.grid(row=2, column=0)
blacklist_textbox.grid(row=2, column=1)
player_label.grid(row=3, column=0)
player_textbox.grid(row=3, column=1)


# Chart selection
chart_menu = tk.Frame(root)
generate_chart_button = ttk.Button(chart_menu, text="Generate Chart", command=generate_chart)
chart_cards_custom_label = tk.Label(chart_menu, text="Optional - Chart these cards in the selected data sample")
chart_cards_preset_label = tk.Label(chart_menu, text="Or choose a preset group")
chart_dropdown = tk.StringVar()
chart_dropdown.set(list(card_groups.CARD_GROUP_DICT.keys())[0])
chart_cards_dropdown = tk.OptionMenu(chart_menu, chart_dropdown, *card_groups.CARD_GROUP_DICT.keys())
chart_cards_textbox = tk.Text(chart_menu, height=1, width=25)

chart_cards_custom_label.grid(row=0, column=0)
chart_cards_textbox.grid(row=0, column=1)
generate_chart_button.grid(row=0, column=2)
chart_cards_preset_label.grid(row=1, column=0)
chart_cards_dropdown.grid(row=1, column=1)


# Output
output_textbox = scrolledtext.ScrolledText(root, state="disabled", width=80, height=10, wrap=tk.WORD)


# Populate window
file_picker_button.grid(row=0, column=0)
date_menu.grid(row=0, column=1)
deck_location_menu.grid(row=1, column=0)
event_type_menu.grid(row=1, column=1)
text_input_menu.grid(row=2, columnspan=2)
analyze_decks_button.grid(row=3, column=0)
show_decks_button.grid(row=3, column=1)
chart_menu.grid(row=4, columnspan=2)
output_textbox.grid(row=6, columnspan=2)


# Draw window
mainframe = ttk.Frame(root)
root.mainloop()
