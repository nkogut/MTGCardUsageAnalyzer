import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import orjson as json
import pandas as pd
from datetime import *
from typing import Optional
from unidecode import unidecode
from collections import defaultdict, Counter
from pathlib import Path
import logging

import config
import utils

logger = logging.getLogger(__name__)

class Scraper:
    """
    A context manager for scraping, parsing, and storing MTGO decklists.

    This class fetches MTGO tournament results with a headless Selenium driver 
    and aggregates daily metagame trends.
    """

    def __init__(self, dataset_path: Path):
        self.dataset_path = dataset_path
        self.url_file = config.DATA_DIR / f"{dataset_path.stem}{config.URLS_FILE_SUFFIX}"
        self.driver = None

    def __enter__(self):
        logger.info("Starting scraper")
        chrome_options = Options()
        chrome_options.page_load_strategy = 'eager'
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            return self
        except selenium.common.exceptions.WebDriverException as e:
            logger.error("Issue with ChromeDriver, cannot create Selenium Session")
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info("Closing scraper")
        if self.driver:
            self.driver.quit()

    def process_event_urls(self, urls: list[str], kill_failures: bool = False) -> None:
        """Visit each url to extract deck information.

        Update dataset_path and the dataset's "urls file" to track visited pages.
        """
        if not urls:
            return

        dataset_name = self.dataset_path.stem
        visited_urls = {"completed": [], "failed": [], "discarded": []}
        decks = []
        daily_counts = defaultdict(Counter)

        logger.info(f"Scraping {len(urls)} events")

        for url in urls:
            url_ending = url.replace(config.MTGO_DECKLIST_PREFIX, "")
            status, content = self._fetch_decklist_elements(url, kill_failures)
            visited_urls[status].append(url_ending)
            
            if status != "completed":
                continue

            for decklist in content:
                deck_dict, parsed_cards = self._parse_deck(decklist.text, url_ending)
                decks.append(deck_dict)
                
                timestamp = pd.to_datetime(deck_dict["date"])
                if timestamp >= config.AGG_START_DATE:
                    for card, quantity in parsed_cards.items():
                        daily_counts[timestamp][card] += quantity

        self._update_play_rates(daily_counts, dataset_name)
        self._update_decklists(decks)
        self._update_urls(visited_urls)

    def fetch_unprocessed_urls(self, format_name: str, date_str: str, kill_failures: bool = False) -> list[str]:
        """Fetch each URL that has not yet been processed."""
        format_name = format_name.title()
        listing_url = f"{config.MTGO_DECKLISTS_LIST_PREFIX}{date_str}?filter={format_name}"
        stored_urls = self._load_urls()

        try:
            self.driver.get(listing_url)
            WebDriverWait(self.driver, config.DRIVER_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "decklists-list"))
            )
        except selenium.common.exceptions.TimeoutException:
            logger.error(f"Unable to access {listing_url}. Please try again with '-retry'")
            if date_str not in stored_urls["failed"]["listing"]:
                stored_urls["failed"]["listing"].append(date_str)
            self._save_urls(stored_urls)
            return []
        
        content = self.driver.find_elements(By.PARTIAL_LINK_TEXT, format_name)

        if not content:
            logger.warning(f"No {format_name} decklists found at {listing_url}")
            if kill_failures:
                if date_str not in stored_urls["failed"]["discarded"]:
                    stored_urls["failed"]["discarded"].append(date_str)
                if date_str in stored_urls["failed"]["listing"]:
                    stored_urls["failed"]["listing"].remove(date_str)
            else:
                if date_str not in stored_urls["failed"]["listing"]:
                    stored_urls["failed"]["listing"].append(date_str)

            self._save_urls(stored_urls)
            return []

        # Filter out urls that are already marked as not being retry candidates (completed or discarded)
        found_urls = [elem.get_attribute("href") for elem in content]
        ignore_list = set(stored_urls["completed"] + stored_urls["failed"]["discarded"])
        
        new_urls = [
            url for url in found_urls 
            if url.replace(config.MTGO_DECKLIST_PREFIX, "") not in ignore_list
        ]

        logger.debug(f"Found {len(found_urls)} URLs for {date_str} - {len(new_urls)} are new")

        if date_str in stored_urls["failed"]["listing"]:
            stored_urls["failed"]["listing"].remove(date_str)

        self._save_urls(stored_urls)
        return new_urls

    def process_date_range(
            self, 
            format_name: str, 
            grace: int = config.DEFAULT_GRACE_DAYS, 
            start_date: str = None, 
            end_date: str = None
        ) -> None:
        """Scrape one or more months of data for one format, and add data to dataset_path."""
        format_name = format_name.capitalize()
        start_date = start_date or (datetime.today() - timedelta(days=grace)).strftime(config.DATE_FMT_CLI)
        end_date = end_date or datetime.today().strftime(config.DATE_FMT_CLI)

        if start_date > end_date:
            logger.error(f"Start Date ({start_date}) comes after End Date ({end_date})")
            return

        dates = utils.get_dates_between_months(start_date, end_date)
        logger.debug(f"Processing date range {start_date} to {end_date} ({len(dates)} days total)")

        for date_str in dates:
            new_urls = self.fetch_unprocessed_urls(format_name, date_str)
            self.process_event_urls(new_urls)

    def retry_backlog_urls(self, format_name: str, kill_failures: bool = False) -> None:
        """Retry all previously failed listing and event URLs."""
        urls = self._load_urls()

        num_failed_events = len(urls["failed"]["event"])
        num_failed_listings = len(urls["failed"]["listing"])

        for date_str in urls["failed"]["listing"]:
            new_urls = self.fetch_unprocessed_urls(format_name, date_str, kill_failures=kill_failures)
            self.process_event_urls(new_urls, kill_failures=kill_failures)

        if num_failed_events > 0:
            urls = self._load_urls()
            
        full_urls = [f"{config.MTGO_DECKLIST_PREFIX}{url_ending}" for url_ending in urls["failed"]["event"]]

        if full_urls:
            self.process_event_urls(full_urls, kill_failures=kill_failures)

        urls = self._load_urls()
        
        new_num_events = len(urls["failed"]["event"])
        new_num_listings = len(urls["failed"]["listing"])

        logger.info(
            "\n--- Retry Summary ---\n"
            f"Months retried: {num_failed_listings:03d} (Remaining: {new_num_listings:03d})\n"
            f"Events retried: {num_failed_events:03d} (Remaining: {new_num_events:03d})\n"
            "---------------------"
        )
    
    def _update_decklists(self, new_decks: list[dict]) -> None:
        """Merge new decklists with the existing dataset in chronological order based on tournament date."""
        if not new_decks:
            return

        stored_decks = []
        if self.dataset_path.is_file():
            stored_decks = json.loads(self.dataset_path.read_bytes())
        
        stored_decks.extend(new_decks)
        stored_decks.sort(key=lambda x: x["date"])

        logger.info(f"Saving {len(new_decks)} decklists to {self.dataset_path}")
        self.dataset_path.write_bytes(json.dumps(stored_decks))

    def _load_urls(self) -> dict:
        """Load the URLs for the current dataset or initialize default URL lists."""
        if self.url_file.is_file():
            return json.loads(self.url_file.read_bytes())
        
        return {"completed": [], "failed": {"listing": [], "event": [], "discarded": []}}

    def _save_urls(self, urls_data: dict) -> None:
        """Save the URLs dictionary to this dataset's URL file."""
        self.url_file.write_bytes(json.dumps(urls_data))

    def _update_urls(self, visited_urls: dict) -> None:
        """Append visited URLs and remove successful/discarded URLs from the backlog."""
        stored_urls = self._load_urls()
        stored_urls["completed"].extend(visited_urls["completed"])
        
        urls_to_drop = set(visited_urls["completed"] + visited_urls["discarded"])
        still_failed = [url for url in stored_urls["failed"]["event"] if url not in urls_to_drop]
        
        stored_urls["failed"]["event"] = list(set(still_failed + visited_urls["failed"]))
        stored_urls["failed"]["discarded"] = list(set(stored_urls["failed"]["discarded"] + visited_urls["discarded"]))

        if num_errors := len(visited_urls["failed"]):
            logger.warning(
                f"Failed to reach {num_errors} Url{'s' if num_errors > 1 else ''}. "
                f"Please try them again with 'python scrape.py <dataset> <format> -retry'"
            )
        
        if num_discarded := len(visited_urls["discarded"]):
            logger.debug(f"\n_killed {num_discarded} urls")

        self._save_urls(stored_urls)

    def _update_play_rates(self, daily_counts: dict, dataset_name: str) -> None:
        """Convert daily play counts to a DataFrame, merge with existing parquet data, and save."""
        rows = []
        for date, counter in daily_counts.items():
            for card, count in counter.items():
                rows.append((date, dataset_name, card, count))

        if not rows:
            return

        new_df = pd.DataFrame(rows, columns=["date", "format", "card", "count"])
        new_df = new_df.set_index(["date", "format", "card"])

        if config.AGG_PLAY_RATE_PATH.exists():
            existing_df = pd.read_parquet(config.AGG_PLAY_RATE_PATH)
            logger.debug(f"Merging {len(new_df)} new play rate records. Current count: {len(existing_df)}")
            df = pd.concat([existing_df, new_df])
        else:
            logger.debug(f"Initializing new play rate parquet with {len(new_df)} records")
            df = new_df

        df.groupby(level=["date", "format", "card"]).sum().sort_index().to_parquet(config.AGG_PLAY_RATE_PATH, compression="snappy")

    def _fetch_decklist_elements(self, url: str, kill_failures: bool) -> tuple[str, list]:
        """Fetch the decklist URL and wait for the DOM to load. Return the status and deck elements."""
        try:
            self.driver.get(url)
            
            WebDriverWait(self.driver, config.DRIVER_TIMEOUT).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CLASS_NAME, "decklist-item-page")),
                    EC.presence_of_element_located((By.CLASS_NAME, "decklist-title"))
                )
            )
            
            content = self.driver.find_elements(By.CLASS_NAME, "decklist")
            
            if not content:
                # Page loaded but no decks found on it
                if self.driver.find_elements(By.CLASS_NAME, "decklist-posted-on"): 
                    logger.warning(f"{url} has no decks. Discarding it permanently.")
                    return "discarded", []
                
                logger.warning(f"No decks found at {url}. Please retry it.")
                return "discarded" if kill_failures else "failed", []

            # Broken urls and those during high server load can redirect ot the montly urls page
            if self.driver.find_elements(By.CLASS_NAME, "decklists-page"):
                logger.warning(f"Was redirected from {url}")
                return "discarded" if kill_failures else "failed", []
                
            logger.info(f"Gathering {len(content)} decks from {url}")
            return "completed", content
            
        except selenium.common.exceptions.TimeoutException:
            logger.warning(f"Failed to reach {url}. Please retry it.")
            return "discarded" if kill_failures else "failed", []

    def _parse_deck(self, decklist_text: str, url_ending: str) -> tuple[dict, dict]:
        """Parse raw text from a deck element into a dict and card frequency count."""
        deck_contents = decklist_text.split("\n")
        player = unidecode(deck_contents[0].split(" ")[0])
        deck = {
            "date": self._date_from_url(url_ending), 
            "player": player, 
            "url": url_ending, 
            "main": {}, 
            "side": {}
        }
        
        parsed_cards = {}
        is_mainboard = True
        
        for i in range(config.DECK_START_INDEX, len(deck_contents)):
            if "Sideboard" in deck_contents[i]:
                is_mainboard = False
                continue

            # Skip section headers (e.g. "Planeswalkers (3)")
            for t in config.CARD_TYPE_SEPARATORS:
                if t in deck_contents[i]:
                    break
            else:
                quantity, raw_card = deck_contents[i].split(" ", 1)
                card = unidecode(raw_card).lower().split("/")[0] 
                
                if is_mainboard:
                    deck["main"][card] = int(quantity)
                else:
                    deck["side"][card] = int(quantity)
                    
                parsed_cards[card] = parsed_cards.get(card, 0) + int(quantity)
                
        return deck, parsed_cards

    def _date_from_url(self, url: str) -> str:
        *_, year, month, day = url.split("-")
        return f"{int(year)}-{int(month):02d}-{int(day[:2]):02d}"
