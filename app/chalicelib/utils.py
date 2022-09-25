import datetime as dt
import logging
import os

from chalicelib.scraper import ScheduleScraper

LOGGER = logging.getLogger(__name__)


def get_current_season():
    if dt.datetime.now().month >= 7:
        return dt.datetime.now().year

    return dt.datetime.now().year - 1


def populate_empty_schedule(table):
    current_season = get_current_season()
    seasons = [current_season - 1, current_season]
    for season in seasons:
        LOGGER.info("Scraping season %s", season)
        schedule_scraper = ScheduleScraper(season)
        schedule_df = schedule_scraper.season_schedule
        with table.batch_writer() as batch:
            for _, row in schedule_df.iterrows():
                batch.put_item(Item=row.to_dict())


def is_table_empty(table):
    """Takes DynamoDB Table resource, returns true if empty."""
