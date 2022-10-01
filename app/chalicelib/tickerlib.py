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
            ]
        )

    @staticmethod
    def put_game_onto_eventbridge(game_id):
        eb = boto3.client("events")
        response = eb.put_events(
            Entries=[
                {
                    "Source": "ticker",
                    "Detail": json.dumps(dict(game_id=game_id)),
                    "DetailType": "game_to_scrape",
                }
            ]
        )
        if response["FailedEntryCount"]:
            LOGGER.info("Event put failed")
        LOGGER.info("Game %s put onto EventBridge", game_id)

    def run(self):
        LOGGER.info("Checking for new games to scrape...")
        for game_id in self.game_ids_to_scrape:
            LOGGER("%s new games to scrape, queuing...")
            self.put_game_onto_eventbridge(game_id)
            # TODO there's no mechanism for updating the schedule_table.has_been_scraped?
