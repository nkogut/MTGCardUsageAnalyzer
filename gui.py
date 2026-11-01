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

DEFAULT_DATASET_FILE = "Data/modern.json"
dataset = DEFAULT_DATASET_FILE

search_params = {"whitelist": [], "blacklist": [], "player": None, "min_date": date(2000, 1, 1),
                      "max_date": date(2100, 1, 1), "search_in": ["main", "side"],
                      "event_type": ["league", "scheduled"]}

def choose_file() -> None:
    global dataset
    dataset = askopenfilename()

def parse_comma_separated_input(input: str) -> list[str]:
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

def update_search_params() -> None:
    """
    Update query parameters with current gui state and use ca.get_decks() to get all relevant decks
    This is called by the "Analyze Decks", "Show Decks" and "Generate Chart" buttons, which pass it to other functions from CA to format it
    """
    # Set which part of deck to search in
    if not (search_sideboard.get() + search_maindeck.get()) % 2 == 0:
        if search_maindeck.get() == 0:
            search_params["search_in"] = ["side"]
        else:
            search_params["search_in"] = ["main"]
    else:
        search_params["search_in"] = ["main", "side"]

    # Set which types of events to search in
    if not (search_league.get() + search_scheduled.get()) % 2 == 0:
        if search_league.get() == 0:
            search_params["event_type"] = ["scheduled"]
        else:
            search_params["event_type"] = ["league"]
    else:
        search_params["event_type"] = ["league", "scheduled"]

    # Set the date range
    min_date = min_date_selector.get_date()
    max_date = max_date_selector.get_date()
    if min_date > max_date:
        update_output("End date is before start date")
        return
    search_params["min_date"] = min_date
    search_params["max_date"] = max_date

    # Set whitelist/blacklist
    search_params["whitelist"] = parse_comma_separated_input(whitelist_textbox.get(1.0, "end-1c"))
    search_params["blacklist"] = parse_comma_separated_input(blacklist_textbox.get(1.0, "end-1c"))

    # Set Player
    player_input = player_textbox.get(1.0, "end-1c")
    if player_input == "":
        search_params["player"] = None
    else:
        search_params["player"] = player_input

def generate_chart() -> None:
    update_search_params()
    input_chart = parse_comma_separated_input(chart_textbox.get(1.0, "end-1c"))
    print(search_params)
    if not input_chart:
        # Use dropdown
        cards = card_groups.CARD_GROUP_DICT[chart_dropdown_value.get()]
    else:
        # use text input
        cards = input_chart
    dv.create_line_chart(considered_decks=ca.get_decks(dataset, *search_params.values()),
                        cards=cards)


def query_decks() -> list[dict[str, Union[str, dict[str, int]]]]:
    update_search_params()
    return ca.get_decks(dataset, *search_params.values())

# Window setup
root = tk.Tk()
root.title("MTG Card Usage Analyzer")

# Dataset selection
file_picker_button = ttk.Button(root, text="Change Dataset", command=choose_file)
analyze_decks_button = ttk.Button(root, text="Analyze Decks", command=lambda: update_output(ca.get_card_prevalence(query_decks())))
show_decks_button = ttk.Button(root, text="Show Decks", command=lambda: update_output(ca.display_decks(query_decks())))

# Maindeck/Sideboard selection
search_maindeck = tk.Int_var(value=1)
search_sideboard = tk.Int_var(value=1)
search_in_menu = tk.Frame(root)
search_in_menu_label = tk.Label(search_in_menu, text="Search in:")
search_in_maindeck_checkbox = ttk.Checkbutton(search_in_menu, text="Maindeck", variable=search_maindeck)
search_in_sideboard_checkbox = ttk.Checkbutton(search_in_menu, text="Sideboard", variable=search_sideboard)

search_in_menu_label.grid(row=0, columnspan=2)
search_in_maindeck_checkbox.grid(row=1, column=0)
search_in_sideboard_checkbox.grid(row=1, column=1)


#Event type selection
search_league = tk.Int_var(value=1)
search_scheduled = tk.Int_var(value=1)
event_type_menu = tk.Frame(root)
event_type_menu_label = tk.Label(event_type_menu, text="Event types:")
league_checkbox = ttk.Checkbutton(event_type_menu, text="Leagues", variable=search_league)
scheduled_checkbox = ttk.Checkbutton(event_type_menu, text="Scheduled", variable=search_scheduled)

event_type_menu_label.grid(row=0, columnspan=2)
league_checkbox.grid(row=1, column=0)
scheduled_checkbox.grid(row=1, column=1)


#Date selection
date_menu = tk.Frame(root)
default_start_date = date.today() - relativedelta(months=6)
min_date_label = tk.Label(date_menu, text="Start date:")
max_date_label = tk.Label(date_menu, text="End date:")
min_date_selector = Date_entry(date_menu, year=default_start_date.year, month=default_start_date.month, day=1)
max_date_selector = Date_entry(date_menu)

min_date_label.grid(row=0, column=0)
max_date_label.grid(row=0, column=1)
min_date_selector.grid(row=1, column=0)
max_date_selector.grid(row=1, column=1)


# Whitelist/Blacklist selection
card_list_input_menu = tk.Frame(root)
whitelist_label = tk.Label(card_list_input_menu, text="Decks including:")
blacklist_label = tk.Label(card_list_input_menu, text="Excluding decks with:")
player_label = tk.Label(card_list_input_menu, text="Player (up to 1)")
card_list_input_instruction_label = tk.Label(card_list_input_menu, text="Enter as 'card a,card b,card c'")
whitelist_textbox = tk.Text(card_list_input_menu, height=1, width=25)
blacklist_textbox = tk.Text(card_list_input_menu, height=1, width=25)
player_textbox = tk.Text(card_list_input_menu, height=1, width=15)

card_list_input_instruction_label.grid(row=0, column=1)
whitelist_label.grid(row=1, column=0)
whitelist_textbox.grid(row=1, column=1)
blacklist_label.grid(row=2, column=0)
blacklist_textbox.grid(row=2, column=1)
player_label.grid(row=3, column=0)
player_textbox.grid(row=3, column=1)


# Chart selection
chart_menu = tk.Frame(root)
generate_chart_button = ttk.Button(chart_menu, text="Generate Historical Graph", command=generate_chart)
custom_chart_label = tk.Label(chart_menu, text="Optional - Graph the prevalence of these cards:")
preset_chart_label = tk.Label(chart_menu, text="Or choose a preset group")
chart_dropdown_value = tk.String_var()
chart_dropdown_value.set(list(card_groups.CARD_GROUP_DICT.keys())[0])
chart_dropdown = tk.Option_menu(chart_menu, chart_dropdown_value, *card_groups.CARD_GROUP_DICT.keys())
chart_textbox = tk.Text(chart_menu, height=1, width=25)

custom_chart_label.grid(row=0, column=0)
chart_textbox.grid(row=0, column=1)
generate_chart_button.grid(row=0, column=2)
preset_chart_label.grid(row=1, column=0)
chart_dropdown.grid(row=1, column=1)


# Output
output_textbox = scrolledtext.Scrolled_text(root, state="disabled", width=160, height=30, wrap=tk.WORD)


# Populate window
file_picker_button.grid(row=0, column=0)
date_menu.grid(row=0, column=1)
search_in_menu.grid(row=1, column=0)
event_type_menu.grid(row=1, column=1)
card_list_input_menu.grid(row=2, columnspan=2)
analyze_decks_button.grid(row=3, column=0)
show_decks_button.grid(row=3, column=1)
chart_menu.grid(row=4, columnspan=2)
output_textbox.grid(row=6, columnspan=2)


# Draw window
mainframe = ttk.Frame(root)
root.mainloop()
