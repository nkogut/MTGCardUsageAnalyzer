import argparse
import ast
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from mtgo_decklist_analyzer.card_metadata import CardMetadata
from mtgo_decklist_analyzer.config import SETTINGS
from mtgo_decklist_analyzer.deck_analyzer import DeckAnalyzer
from mtgo_decklist_analyzer.types import SearchParams

if __name__ == "__main__":
    parser = argparse.ArgumentParser("analyze")

    # XML-related args
    parser.add_argument("-prefs", "-p", nargs="?",
        help="Optional XML file containing default values in addition to given args"
    )
    parser.add_argument("-save", nargs="?",
        help="Save the preferences from this search to an XML file with the given name"
    )

    # Required args (may be provided by XML instead)
    parser.add_argument("-dataset", "-d", nargs="?", help="e.g. 'full_modern'")
    parser.add_argument("-dsPath", nargs="?", help="Relative or absolute path to dataset. e.g. 'Data/'")

    # Optional search args
    parser.add_argument("-start", "-s", nargs="?", help="first month to scrape. e.g. '2025/1'")
    parser.add_argument("-end", "-e", nargs="?", help="last month to scrape. e.g. '2025/10'")
    parser.add_argument("-whitelist", "-w", nargs="*", help="e.g. \"kappa cann\" \"thought monitor\" memnite ...")
    parser.add_argument("-blacklist", "-b", nargs="*", help="e.g. \"kappa cann\" \"thought monitor\" memnite ...")
    parser.add_argument("-player", nargs="?", help="Search only for decks from a specific player")
    parser.add_argument("-type", nargs="*", help="Return only cards of a specific type(s)")
    parser.add_argument("-main", action=argparse.BooleanOptionalAction,
        help="Search only when the card is in the maindeck"
    )
    parser.add_argument("-side", action=argparse.BooleanOptionalAction,
        help="Search only when the card is in the sideboard"
    )
    parser.add_argument("-fprops", action=argparse.BooleanOptionalAction,
        help="Forcefully update the Card Properties dataset"
    )
    parser.add_argument("-event", nargs="*", help="'league' or 'scheduled'")
    parser.add_argument("-lists", "-l", action=argparse.BooleanOptionalAction,
        help="Show full decklists instead of card stats"
    )

    args = vars(parser.parse_args())

    # Parse the XML tree if provided
    if (prefs := args["prefs"]):
        prefs_path = Path(prefs).with_suffix(SETTINGS.extensions.xml)
        try:
            tree = ET.parse(prefs_path)
            root = tree.getroot()
            for child in root:
                # Input overwrites XML
                text = child.text or ""
                if args.get(child.tag) is None and text != "None":
                    value = child.text or ""
                    if "[" in value:
                        value = ast.literal_eval(text)

                    args[child.tag] = value

        except Exception:
            print(f"Error: could not parse {prefs_path}. Please check that it exists and is valid.")
            sys.exit()

    # Save the new XML tree including CLI args if requested by -save
    if args["save"]:
        save_path = Path(args["save"]).with_suffix(SETTINGS.extensions.xml)
        args["save"] = None

        # Build XML tree
        root = ET.Element("prefs")
        for k, v in args.items():
            if k in ["prefs", "save"]: # Ignore these prefs when saving
                continue
            child = ET.Element(k)
            child.text = str(v)
            root.append(child)

        xml = ET.tostring(root, encoding="unicode")
        save_path.write_text(xml)
        print(f"Preferences saved to {save_path}")

    # Check that mandatory values for DeckAnalyzer were included either as input or in XML
    if not args["fprops"] and not args["save"]:
        missing = []
        required_args = ["dataset"]
        for arg in required_args:
            if args.get(arg) is None:
                missing.append(arg)
                print(f"Error: no value specified for {arg}.")
        if missing:
            sys.exit()

    # Dataset resolution
    dataset = None
    if args.get("dataset"):
        dataset = Path(args["dataset"])
        if dataset.suffix != SETTINGS.extensions.json:
            dataset = dataset.with_suffix(SETTINGS.extensions.json)

        if args.get("dsPath"):
            dataset = Path(args["dsPath"]) / dataset

    # Date resolution
    args["start"] = args.get("start") or SETTINGS.dates.default_min_date_str
    args["end"] = args.get("end") or SETTINGS.dates.default_max_date_str

    args["start"] = datetime.strptime(args["start"], SETTINGS.dates.date_fmt_cli).date()
    args["end"] = datetime.strptime(args["end"], SETTINGS.dates.date_fmt_cli).date()

    # Deck / Event
    search_in = []
    if args.get("main"):
        search_in.append("main")
    if args.get("side"):
        search_in.append("side")

    search_in = search_in or None
    force_update_props = bool(args.get("fprops"))

    if dataset is not None:
        card_metadata = CardMetadata(force_update=force_update_props)
        analyzer = DeckAnalyzer(dataset_path=dataset, card_metadata=card_metadata)

        params: SearchParams = {
            "whitelist": args.get("whitelist") or [],
            "blacklist": args.get("blacklist") or [],
            "player": args.get("player"),
            "min_date": args["start"],
            "max_date": args["end"],
            "search_in": search_in or list(SETTINGS.analyzer.search_in_default),
            "event_types": args.get("event") or list(SETTINGS.analyzer.default_event_types)
        }

        decks = analyzer.query_decks(params)

        if args.get("lists"):
            print(analyzer.generate_decklist_report(decks))
        else:
            print(analyzer.generate_card_frequency_report(decks, args.get("type")))
