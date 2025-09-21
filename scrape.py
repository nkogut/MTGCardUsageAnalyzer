import scraper
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser("scrape")
    parser.add_argument("dataset", help="file name with or without file extension. e.g. 'full_modern'")
    parser.add_argument("format", help="Format name to scrape. e.g. 'modern'")
    parser.add_argument("-start", nargs="?", help="first month to scrape. e.g. '2025/1'")
    parser.add_argument("-end", nargs="?", help="last month to scrape. e.g. '2025/10'")
    parser.add_argument("-grace", nargs="?", help="# of days before start date to begin scraping. Intended to prevent coverage issues when automated. \nOnly applies if no start date is given. Default: 7")
    parser.add_argument("-skip", action=argparse.BooleanOptionalAction, help="Skip updating card dictionary references. Only use if no new cards have been added to Scryfall recently")
    
    # Format args and set default values
    args = parser.parse_args()
    if ".json" not in args.dataset:
        args.dataset = args.dataset + ".json"

    if args.grace == None:
        args.grace = 7
    args.grace = int(args.grace)

    scraper.getUrlsForMonths(args.dataset, args.format, args.skip, args.grace, args.start, args.end)
