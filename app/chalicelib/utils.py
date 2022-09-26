import datetime as dt
from . import LOGGER
import json

import boto3

from .scraperlib import ScheduleScraper


def get_dynamodb_table(table_name):
    ddb = boto3.resource("dynamodb")
    return ddb.Table(table_name)


def get_current_season():
    if dt.datetime.now().month >= 7:
        return dt.datetime.now().year
    return dt.datetime.now().year - 1


def add_dict_to_dynamodb(dict_, table):
    table.put_item(Item=dict_)


def scrape_season_schedule_into_db(season, table):
    LOGGER.info("Scraping season %s", season)
    schedule_scraper = ScheduleScraper(season)
    schedule_df = schedule_scraper.season_schedule
    with table.batch_writer() as batch:
        for _, row in schedule_df.iterrows():
            batch.put_item(Item=row.to_dict())
    LOGGER.info("Season %s scraped into database", season)


def populate_empty_schedule(table, back_seasons=0):
    current_season = get_current_season()
    seasons = [current_season]
    if back_seasons:
        seasons.extend([current_season - n for n in range(seasons + 1)])
    for season in seasons:
        scrape_season_schedule_into_db(season, table)


def new_seasons_at_source(table):
    seasons_in_db = sorted(
        list(set([int(d["season"][:4]) for d in table.scan()["Items"]]))
    )
    schedule_scraper = ScheduleScraper()
    seasons_at_source = schedule_scraper.seasons_at_source
    num_new_seasons = max(seasons_at_source) - max(seasons_in_db)
    if num_new_seasons > 0:
        return seasons_at_source[-num_new_seasons:]


def get_game_ids_to_scrape(table):
    return sorted(
        [
            d["id"]
            for d in table.scan()["Items"]
            if all([d["has_data"], not d["has_been_scraped"]])
        ]
    )


def put_onto_eventbridge(source, detail, detail_type):
    """Put an event onto EventBridge.

    Args:
        source (str): source
        detail (dict): detail as dict
        detail_type (str): detail type

    """
    eb = boto3.client("events")
    response = eb.put_events(
        Entries=[
            {
                "Source": source,
                "Detail": json.dumps(detail),
                "DetailType": detail_type,
            }
        ]
    )
    if response["FailedEntryCount"]:
        LOGGER.info("Event put failed")
    LOGGER.info("Event put onto EventBridge")
