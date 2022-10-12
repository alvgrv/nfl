"""Schedule-driven data fetch function."""
import json

import boto3

from . import LOGGER
from .table import DataTable
from .scraper import ScheduleScraper


class Ticker:
    """Schedule-driven function to publish events containing game_ids to be scraped."""

    def __init__(self, data_table: DataTable, schedule_scraper: ScheduleScraper):
        """Initialise class with dependency injection of DataTable, ScheduleScraper."""
        self.data_table = data_table
        self.schedule_scraper = schedule_scraper

    @property
    def game_ids_to_scrape(self):
        """Returns list of game_ids with data at source but not found in data table."""
        return [
            g
            for g in sorted(self.schedule_scraper.games_with_data)
            if g not in self.data_table.game_ids
        ]

    @staticmethod
    def put_games_onto_eventbridge(game_ids):
        """Publishes game ids to EventBridge.

        Args:
            game_ids (list): list of game_ids to scrape

        """
        eb = boto3.client("events")
        for gid in game_ids:
            response = eb.put_events(
                Entries=[
                    {
                        "Source": "ticker",
                        "Detail": json.dumps(dict(game_id=gid)),
                        "DetailType": "game_to_scrape",
                    }
                ]
            )
            if response["FailedEntryCount"]:
                LOGGER.error("Event put failed")
                LOGGER.error(response["Entries"])
                return
            LOGGER.info("Game ID %s put onto EventBridge", gid)

    def run(self):
        """Execute command."""
        LOGGER.info("%s new games to scrape, queuing...", len(self.game_ids_to_scrape))
        self.put_games_onto_eventbridge(self.game_ids_to_scrape)
