import argparse
import xml.etree.ElementTree as ET
import ast
import string
import card_analyzer as ca

from datetime import datetime
from pathlib import Path

import config


if __name__ == "__main__":
    parser = argparse.ArgumentParser("analyze")
    
    # XML args
    parser.add_argument("-prefs", "-p", nargs="?", help="Optional XML file containing default values in addition to given args")
    parser.add_argument("-save", nargs="?", help="Save the preferences from this search to an XML file with the given name")

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
    parser.add_argument("-main", action=argparse.BooleanOptionalAction, help="Search only when the card is in the maindeck")
    parser.add_argument("-side", action=argparse.BooleanOptionalAction, help="Search only when the card is in the sideboard")
    parser.add_argument("-fprops", action=argparse.BooleanOptionalAction, help="Forcefully update the Card Properties dataset")
    parser.add_argument("-event", nargs="*", help="'league' or 'scheduled'")
    parser.add_argument("-lists", "-l", action=argparse.BooleanOptionalAction, help="Show full decklists instead of card stats")
    
    args = vars(parser.parse_args())

    # Parse the XML tree if provided
    if (prefs := args["prefs"]):
        prefs_path = Path(prefs).with_suffix(config.XML_EXT)
        try:
            tree = ET.parse(prefs)
            root = tree.getroot()
            for child in root:
                # Input overwrites XML
                if args[child.tag] == None and child.text != "None": 
                    value = child.text
                    if "[" in value:
                        value = ast.literal_eval(child.text)
                    
                    args[child.tag] = value

        except Exception as e: 
            print(f"Error: could not parse {prefs_path}. Please check that it exists and is valid.")
            quit()

    # Save the new XML tree including CLI args if requested by -save
    if args["save"]:
        save_path = Path(args["save"]).with_suffix(config.XML_EXT)
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

    # Check that mandatory values for getDecks were included either as input or in XML
    # First check that no operations that happen separately from these required args are enabled. In that case these are not actually required

    if not args["fprops"] and not args["save"]:
        missing = []
        requiredArgs = ["dataset"]
        for arg in requiredArgs:
            if args[arg] == None:
                missing.append(arg)
                print(f"Error: no value specified for {arg}.")
        if len(missing) > 0:
            quit()


    # Format values to pass to CA:

    # Dataset
    dataset = None
    if args["dataset"]:
        dataset = Path(args["dataset"])
        
        if dataset.suffix != config.JSON_EXT:
            dataset = dataset.with_suffix(config.JSON_EXT)
        
        if args["dsPath"]:
            dataset = Path(args["dsPath"]) / dataset

    # Dates
    args["start"] = args["start"] or config.DEFAULT_MIN_DATE_STR
    args["end"] = args["end"] or config.DEFAULT_MIN_DATE_STR

    args["start"] = datetime.strptime(args["start"], config.DATE_FMT_CLI).date()
    args["end"] = datetime.strptime(args["end"], config.DATE_FMT_CLI).date()

    # Deck / Event
    searchIn = []
    if args["main"]:
        searchIn.append("main")
    if args["side"]:
        searchIn.append("side")

    searchIn = searchIn or None

    if args["fprops"]:
        ca.loadCardProperties(True)

    if dataset != None:
        decks = ca.getDecks(
                        datasetPath=dataset,
                        whitelist=args["whitelist"],
                        blacklist=args["blacklist"],
                        player=args["player"],
                        minDate=args["start"],
                        maxDate=args["end"],
                        searchIn=searchIn,
                        eventType=args["event"]
                    )
    
        if args["lists"]:
            print(ca.displayDecks(decks))
        else:
            print(ca.getCardPrevalence(decks, args["type"]))   
