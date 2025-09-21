import argparse
import xml.etree.ElementTree as ET
import ast
import card_analyzer as ca
from datetime import datetime

if __name__ == "__main__":
    parser = argparse.ArgumentParser("analyze")
    
    # XML args
    parser.add_argument("-prefs", "-p", nargs="?", help="Optional XML file containing default values in addition to given args")
    parser.add_argument("-save", nargs="?", help="Save the preferences from this search to an XML file with the given name")

    # Required args (may be provided by XML instead)
    parser.add_argument("-dataset", "-d", nargs="?", help="e.g. 'full_modern'")
    parser.add_argument("-dsPath", nargs="?", help="Relative or absolute path to dataset. e.g. 'Data/'")
    parser.add_argument("-format", "-f", nargs="?", help="Format name to scrape. e.g. 'modern'")

    # Optional search args
    parser.add_argument("-start", "-s", nargs="?", help="first month to scrape. e.g. '2025/1'")
    parser.add_argument("-end", "-e", nargs="?", help="last month to scrape. e.g. '2025/10'")
    parser.add_argument("-whitelist", "-w", nargs="*", help="e.g. \"kappa cann\" \"thought monitor\" memnite ...")
    parser.add_argument("-blacklist", "-b", nargs="*", help="e.g. \"kappa cann\" \"thought monitor\" memnite ...")
    parser.add_argument("-player", nargs="?", help="Search only for decks from a specific player")
    parser.add_argument("-main", action=argparse.BooleanOptionalAction, help="Search only when the card is in the maindeck")
    parser.add_argument("-side", action=argparse.BooleanOptionalAction, help="Search only when the card is in the sideboard")
    parser.add_argument("-event", nargs="*", help="'league' or 'scheduled'")
    
    args = vars(parser.parse_args())

    # Parse the XML tree if provided
    prefs = args["prefs"]
    if prefs != None:
       try:
            if ".xml" not in prefs:
                prefs += ".xml"
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
           print(f"Error: could not parse {prefs}. Please check that it exists and is valid.")
           quit()

    # Save the new XML tree including CLI args if requested by -save
    saveName = args["save"]
    if saveName != None:
        # User must choose to save each time
        args["save"] = None 
        
        # Build XML tree
        root = ET.Element("prefs")
        for k, v in args.items():
            child = ET.Element(k)
            child.text = str(v)
            root.append(child)

        xml  = ET.tostring(root, encoding="unicode")

        # Save the XML
        if ".xml" not in saveName:
            saveName += ".xml"
        with open(saveName, "w") as f:
            f.write(xml)
            print(f"Preferences saved to {saveName}")

    # Check that mandatory values were included either as input or in XML
    missing = []
    for arg in ["dataset", "format"]:
        if args[arg] == None:
            missing.append(arg)
            print(f"Error: no value specified for {arg}.")
    if len(missing) > 0:
        quit()


    # Format values to pass to CA:

    # Dataset
    dataset = args["dataset"]

    if ".json" not in dataset:
        dataset += ".json"
    
    if args["dsPath"] != None:
        if args["dsPath"][-1] != "/":
            args["dsPath"] += "/"
        dataset = args["dsPath"] + dataset

    # Dates
    if args["start"] == None:
        args["start"] = "2010/01"

    if args["end"] == None:
        args["end"] = "2110/01"

    args["start"] = datetime.strptime(args["start"], "%Y/%m").date()
    args["end"] = datetime.strptime(args["end"], "%Y/%m").date()

    # Deck / Event
    search_in = []
    if args["main"]:
        search_in.append("maindeck")
    if args["side"]:
        search_in.append("sideboard")

    if len(search_in) == 0:
        search_in = None

    if args["event"] != None:
        args["event"] = [value.lower() for value in args["event"]]

    # Make call to card_analyzer
    print(
        ca.find_card_prevalence(
            ca.find_decks(
                dataset=dataset,
                whitelist=args["whitelist"],
                blacklist=args["blacklist"],
                player=args["player"],
                min_date=args["start"],
                max_date=args["end"],
                search_in=search_in,
                event_type=args["event"]
            ),
            search_in=search_in
        )
    )        
