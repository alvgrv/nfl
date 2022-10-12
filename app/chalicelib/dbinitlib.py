from .tickerlib import Ticker
from .utils import get_dynamodb_table, get_current_season
from .scraperlib import ScheduleScraper
from . import LOGGER
import os
import boto3


class DataTable:
    def __init__(self):
        self.ddb = boto3.resource("dynamodb")
        self.name = os.environ["DATA_TABLE"]
        self.table = self.ddb.Table(self.name)

    @staticmethod
    def scan_for_attributes(self, *args):
        return self.table.scan(AttributesToGet=list(args))["Items"]

    @property
    def match_ids(self):
        return self.scan_for_attributes("match_id")

    @property
    def seasons(self):
        return self.scan_for_attributes("season")

    @property
    def all_rows(self):
        return self.table.scan()["Items"]


#
# class DatabaseInit:
#     def __init__(self, data_table: DataTable):
#         self.data_table = data_table
#
#     @property
#     def current_season(self):
#         return get_current_season()
#
#     @property
#     def new_seasons_at_source(self):
#         max_season_at_db = max(
#             set([int(d["season"][:4]) for d in self.data_table.seasons]), default=0
#         )
#         seasons_at_source = ScheduleScraper.get_all_seasons_at_source()
#         max_season_at_source = max(seasons_at_source, default=0)
#         num_new_seasons = max_season_at_db - max_season_at_source
#         if num_new_seasons > 0:
#             return seasons_at_source[-num_new_seasons:]
#
#     def scrape_season_schedule(self, season):
#         LOGGER.info("Scraping season %s", season)
#         schedule_scraper = ScheduleScraper(season)
#         schedule_df = schedule_scraper.season_schedule
#         with self.data_table.table.batch_writer() as batch:
#             for _, row in schedule_df.iterrows():
#                 batch.put_item(Item=row.to_dict())
#         LOGGER.info("Season %s scraped into database", season)
#
#     def populate_empty_schedule(self, back_seasons=0):
#         seasons = [self.current_season]
#         if back_seasons:
#             seasons.extend([self.current_season - n for n in range(back_seasons + 1)])
#         for season in seasons:
#             self.scrape_season_schedule(season)
#
#     def run(self):
#         if self.data_table.all_rows:
#             LOGGER.info("Checking years up to date...")
#             if self.new_seasons_at_source:
#                 LOGGER.info("New season(s) found at source")
#                 for season in self.new_seasons_at_source:
#                     LOGGER.info("Scraping season %s schedule...", season)
#                     self.scrape_season_schedule(season)
#         else:
#             LOGGER.info("Schedule table empty, populating...")
#             self.populate_empty_schedule()
#
#         ticker = Ticker()
#         ticker.run()
