import os
from .utils import get_dynamodb_table
import boto3
from . import LOGGER
import json


class Ticker:
    def __init__(self):
        self.schedule_table = get_dynamodb_table(os.environ["SCHEDULE_TABLE"])
        self.schedule_table_query = self.schedule_table.scan()
        self.schedule_table_results = self.schedule_table_query["Items"]
        self.data_table = get_dynamodb_table(os.environ["DATA_TABLE"])
        self.data_table_query = self.data_table.scan()
        self.data_table_results = self.data_table_query["Items"]

    @property
    def game_ids_to_scrape(self):
        return sorted(
            [
                d["id"]
                for d in self.schedule_table_results
                if all([d["has_data"], not d["has_been_scraped"]])
            ]  # TODO no mechanism for updating has_data either?
        )

    @staticmethod
    def put_games_onto_eventbridge(game_ids):
        eb = boto3.client("events")
        response = eb.put_events(
            Entries=[
                {
                    "Source": "ticker",
                    "Detail": json.dumps(dict(game_ids=game_ids)),
                    "DetailType": "games_to_scrape",
                }
            ]
        )
        if response["FailedEntryCount"]:
            LOGGER.info("Event put failed")
            return
        LOGGER.info("Games IDs put onto EventBridge:")
        for g in game_ids:
            LOGGER.info(g)

    def run(self):
        LOGGER.info("%s new games to scrape, queuing...")
        self.put_games_onto_eventbridge(self.game_ids_to_scrape)
        # TODO there's no mechanism for updating the schedule_table.has_been_scraped?
