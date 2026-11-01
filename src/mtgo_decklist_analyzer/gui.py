import tkinter as tk
import tkinter.font as tkfont
from datetime import date
from pathlib import Path
from tkinter import scrolledtext, ttk
from tkinter.filedialog import askopenfilename

from dateutil.relativedelta import relativedelta
from tkcalendar import DateEntry

from mtgo_decklist_analyzer.card_metadata import CardMetadata
from mtgo_decklist_analyzer.config import CARD_GROUPS
from mtgo_decklist_analyzer.data_visualization import create_line_chart
from mtgo_decklist_analyzer.deck_analyzer import DeckAnalyzer
from mtgo_decklist_analyzer.types import DeckEntries, SearchParams

DEFAULT_DATASET_FILE = Path("data/modern.json")


class AnalyzerGUI:
    """GUI application for filtering and displaying decks and metagames through text or charts."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MTG Card Usage Analyzer")

        self.dataset_path = DEFAULT_DATASET_FILE
        self.card_meta = CardMetadata()
        self.analyzer = DeckAnalyzer(dataset_path=self.dataset_path, card_metadata=self.card_meta)

        self.search_params: SearchParams = {
            "whitelist": [],
            "blacklist": [],
            "player": None,
            "min_date": date(2000, 1, 1),
            "max_date": date(2100, 1, 1),
            "search_in": ["main", "side"],
            "event_types": ["league", "scheduled"]
        }

        self._build_ui()

    def _build_ui(self) -> None:  # noqa: PLR0915
        """Construct the initial UI layout and state."""
        # Dataset selection
        self.file_picker_button = ttk.Button(self.root, text="Change Dataset", command=self._choose_file)
        self.analyze_decks_button = ttk.Button(self.root, text="Analyze Decks", command=self._analyze_decks)
        self.show_decks_button = ttk.Button(self.root, text="Show Decks", command=self._show_decks)

        # Maindeck/Sideboard selection
        self.search_maindeck_var = tk.IntVar(value=1)
        self.search_sideboard_var = tk.IntVar(value=1)
        self.search_in_menu = tk.Frame(self.root)
        self.search_in_menu_label = tk.Label(self.search_in_menu, text="Search in:")
        self.search_in_maindeck_checkbox = ttk.Checkbutton(
            self.search_in_menu, text="Maindeck", variable=self.search_maindeck_var
        )
        self.search_in_sideboard_checkbox = ttk.Checkbutton(
            self.search_in_menu, text="Sideboard", variable=self.search_sideboard_var
        )

        self.search_in_menu_label.grid(row=0, columnspan=2)
        self.search_in_maindeck_checkbox.grid(row=1, column=0)
        self.search_in_sideboard_checkbox.grid(row=1, column=1)

        # Event type selection
        self.search_league_var = tk.IntVar(value=1)
        self.search_scheduled = tk.IntVar(value=1)
        self.event_type_menu = tk.Frame(self.root)
        self.event_type_menu_label = tk.Label(self.event_type_menu, text="Event types:")
        self.league_checkbox = ttk.Checkbutton(
            self.event_type_menu,
            text="Leagues",
            variable=self.search_league_var
        )
        self.scheduled_checkbox = ttk.Checkbutton(
            self.event_type_menu,
            text="Scheduled",
            variable=self.search_scheduled
        )

        self.event_type_menu_label.grid(row=0, columnspan=2)
        self.league_checkbox.grid(row=1, column=0)
        self.scheduled_checkbox.grid(row=1, column=1)

        # Date selection
        self.date_menu = tk.Frame(self.root)
        default_start_date = date.today() - relativedelta(months=6)
        self.min_date_label = tk.Label(self.date_menu, text="Start date:")
        self.max_date_label = tk.Label(self.date_menu, text="End date:")
        self.min_date_selector = DateEntry(
            self.date_menu, year=default_start_date.year, month=default_start_date.month, day=1
        )
        self.max_date_selector = DateEntry(self.date_menu)

        self.min_date_label.grid(row=0, column=0)
        self.max_date_label.grid(row=0, column=1)
        self.min_date_selector.grid(row=1, column=0)
        self.max_date_selector.grid(row=1, column=1)

        # Whitelist/Blacklist selection
        self.card_list_input_menu = tk.Frame(self.root)
        self.whitelist_label = tk.Label(self.card_list_input_menu, text="Decks including:")
        self.blacklist_label = tk.Label(self.card_list_input_menu, text="Excluding decks with:")
        self.player_label = tk.Label(self.card_list_input_menu, text="Player (up to 1)")
        self.card_list_input_instruction_label = tk.Label(self.card_list_input_menu, text="Enter as 'card a;card b'")

        self.whitelist_entry = ttk.Entry(self.card_list_input_menu, width=50)
        self.blacklist_entry = ttk.Entry(self.card_list_input_menu, width=50)
        self.player_entry = ttk.Entry(self.card_list_input_menu, width=25)

        # Bind tabbing/clicking away to trigger name resolution
        self.whitelist_entry.bind("<FocusOut>", lambda _: self._format_entry(self.whitelist_entry))
        self.blacklist_entry.bind("<FocusOut>", lambda _: self._format_entry(self.blacklist_entry))

        self.card_list_input_instruction_label.grid(row=0, column=1)
        self.whitelist_label.grid(row=1, column=0)
        self.whitelist_entry.grid(row=1, column=1)
        self.blacklist_label.grid(row=2, column=0)
        self.blacklist_entry.grid(row=2, column=1)
        self.player_label.grid(row=3, column=0)
        self.player_entry.grid(row=3, column=1)

        # Chart selection
        self.chart_menu = tk.Frame(self.root)
        self.generate_chart_button = ttk.Button(self.chart_menu, text="Generate Graph", command=self._generate_chart)
        self.custom_chart_label = tk.Label(self.chart_menu, text="Optional - Graph the prevalence of these cards:")
        self.preset_chart_label = tk.Label(self.chart_menu, text="Or choose a preset group")

        max_cg_len = max((len(f) for f in CARD_GROUPS), default=0)
        self.card_groups = {
            f"{fmt:\u00A0<{max_cg_len + 1}} | {group}": cards
            for fmt, section in CARD_GROUPS.items()
            for group, cards in section.items()
        }
        self.chart_dropdown_value = tk.StringVar()
        group_keys = list(self.card_groups.keys())

        if group_keys:
            self.chart_dropdown_value.set(group_keys[0])
            self.chart_dropdown = ttk.Combobox(
                self.chart_menu,
                textvariable=self.chart_dropdown_value,
                values=group_keys,
                state="readonly",
                width=max(len(k) for k in group_keys) + 1
            )

        self.chart_entry = ttk.Entry(self.chart_menu, width=50)
        self.chart_entry.bind("<FocusOut>", lambda e: self._format_entry(self.chart_entry))

        self.custom_chart_label.grid(row=0, column=0)
        self.chart_entry.grid(row=0, column=1)
        self.generate_chart_button.grid(row=0, column=2)
        self.preset_chart_label.grid(row=1, column=0)
        self.chart_dropdown.grid(row=1, column=1)

        # Output
        self.output_textbox = scrolledtext.ScrolledText(self.root, state="disabled", width=160, height=30, wrap=tk.WORD)

        # Populate window
        self.file_picker_button.grid(row=0, column=0)
        self.date_menu.grid(row=0, column=1)
        self.search_in_menu.grid(row=1, column=0)
        self.event_type_menu.grid(row=1, column=1)
        self.card_list_input_menu.grid(row=2, columnspan=2)
        self.analyze_decks_button.grid(row=3, column=0)
        self.show_decks_button.grid(row=3, column=1)
        self.chart_menu.grid(row=4, columnspan=2)
        self.output_textbox.grid(row=6, columnspan=2)

    def _choose_file(self) -> None:
        """Prompt user for a new dataset file and re-initialize the deck analyzer object."""
        if new_file := askopenfilename():
            self.dataset_path = Path(new_file)
            self.analyzer = DeckAnalyzer(dataset_path=self.dataset_path, card_metadata=self.card_meta)

    def _format_entry(self, entry_widget: ttk.Entry) -> None:
        """Resolve card names in the UI text box when the user tabs out."""
        raw_text = entry_widget.get().strip()
        if not raw_text:
            return

        raw_names = [c.strip() for c in raw_text.split(";") if c.strip()]
        resolved = [self.card_meta.resolve_card_name(c) for c in raw_names]

        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, "; ".join(resolved))

    def _parse_card_name_list(self, text: str) -> list[str]:
        """Parse, normalize, and resolve semicolon-separated card names."""
        if not text:
            return []

        raw_names = [t.strip() for t in text.split(";") if t.strip()]
        return [self.card_meta.resolve_card_name(c) for c in raw_names]

    def _update_output(self, text: str) -> None:
        """Overwrite the output textbox with new text."""
        self.output_textbox.config(state="normal")
        self.output_textbox.delete(1.0, tk.END)
        self.output_textbox.insert(1.0, text)
        self.output_textbox.config(state="disabled")

    def _update_search_params(self) -> bool:
        """Update query parameters with the current state. Return success status."""
        search_in = []
        if self.search_maindeck_var.get():
            search_in.append("main")
        if self.search_sideboard_var.get():
            search_in.append("side")
        self.search_params["search_in"] = search_in if search_in else ["main", "side"]

        event_type = []
        if self.search_league_var.get():
            event_type.append("league")
        if self.search_scheduled.get():
            event_type.append("scheduled")
        self.search_params["event_types"] = event_type if event_type else ["league", "scheduled"]

        min_date = self.min_date_selector.get_date()
        max_date = self.max_date_selector.get_date()
        if min_date > max_date:
            self._update_output("End date is before start date")
            return False

        self.search_params["min_date"] = min_date
        self.search_params["max_date"] = max_date

        self.search_params["whitelist"] = self._parse_card_name_list(self.whitelist_entry.get())
        self.search_params["blacklist"] = self._parse_card_name_list(self.blacklist_entry.get())

        player_input = self.player_entry.get().strip()
        self.search_params["player"] = player_input if player_input else None
        return True

    def _query_decks(self) -> DeckEntries | None:
        """Fetch decks from the analyzer matching current GUI parameters."""
        if self._update_search_params():
            return self.analyzer.query_decks(self.search_params)
        return None

    def _analyze_decks(self) -> None:
        """Generate and display a card frequency report."""
        if (decks := self._query_decks()) is not None:
            self._update_output(self.analyzer.generate_card_frequency_report(decks))

    def _show_decks(self) -> None:
        """Generate and display a decklist report."""
        if (decks := self._query_decks()) is not None:
            self._update_output(self.analyzer.generate_decklist_report(decks))

    def _generate_chart(self) -> None:
        """Generate a historical prevalence graph based on selected cards."""
        if (decks := self._query_decks()) is not None:
            input_chart = self._parse_card_name_list(self.chart_entry.get())
            cards = input_chart if input_chart else self.card_groups[self.chart_dropdown_value.get()]
            create_line_chart(considered_decks=decks, cards=cards)


if __name__ == "__main__":
    root_window = tk.Tk()

    # Use monospace font universally
    for font_name in tkfont.names():
        tkfont.nametofont(font_name).configure(family="Consolas", size=10)
    root_window.option_add("*TCombobox*Listbox.font", "Consolas 10")

    app = AnalyzerGUI(root_window)
    root_window.mainloop()
