import argparse
import logging
from pathlib import Path

from mtgo_decklist_analyzer.config import SETTINGS
from mtgo_decklist_analyzer.scraper import Scraper

if __name__ == "__main__":
    parser = argparse.ArgumentParser("scrape")
    parser.add_argument("dataset", help="file name with or without file extension. e.g. 'full_modern'")
    parser.add_argument("format", help="Format name to scrape. e.g. 'modern'")
    parser.add_argument("-start", nargs="?", help="first month to scrape. e.g. '2025/1'")
    parser.add_argument("-end", nargs="?", help="last month to scrape. e.g. '2025/10'")
    parser.add_argument("-grace", nargs="?",
        help=(
            "# of days before start date to begin scraping. Intended to prevent coverage issues when automated.\n"
            "Only applies if no start date is given. Default: 7"
        ),
    )
    parser.add_argument("-retry", action=argparse.BooleanOptionalAction,
        help="Retry all urls which failed previously instead of a normal scrape.",
    )
    parser.add_argument("-kill", action=argparse.BooleanOptionalAction,
        help=(
            "Retry failed urls, and permanently remove them. "
            "Use after many retries with no improvement."
        ),
    )

    # Format args and set default values
    args = parser.parse_args()

    dataset = Path(args.dataset).with_suffix(SETTINGS.extensions.json)

    args.format = args.format.lower()
    args.grace = SETTINGS.scraper.default_grace_days if args.grace is None else args.grace
    args.grace = int(args.grace)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    with Scraper(dataset) as scraper:
        if args.kill:
            scraper.retry_backlog_urls(args.format, kill_failures=True)
        elif args.retry:
            scraper.retry_backlog_urls(args.format, kill_failures=False)
        else:
            scraper.process_date_range(args.format, grace=args.grace, start_date=args.start, end_date=args.end)
