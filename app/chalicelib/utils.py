import datetime as dt
import logging
import json
import os

import boto3

from .scraper import ScheduleScraper

LOGGER = logging.getLogger("app")


def get_current_season():
    if dt.datetime.now().month >= 7:
        return dt.datetime.now().year
    return dt.datetime.now().year - 1


def scrape_season_schedule_into_db(season, table):
    LOGGER.info("Scraping season %s", season)
    schedule_scraper = ScheduleScraper(season)
    schedule_df = schedule_scraper.season_schedule
    with table.batch_writer() as batch:
        for _, row in schedule_df.iterrows():
            batch.put_item(Item=row.to_dict())
    LOGGER.info("Season %s scraped into database", season)


def populate_empty_schedule(table):
    current_season = get_current_season()
    seasons = [current_season - 1, current_season]
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


def put_onto_eventbridge(game_ids, eb):
    for game_id in game_ids:
        response = eb.put_events(
            Entries=[
                {
                    "Source": "nfl-ticker",
                    "Detail": json.dumps({"game_id": game_id}),
                    "DetailType": "game_to_scrape",
                }
            ]
        )
        if response["FailedEntryCount"]:
            LOGGER.info("Event put failed for game_id %s", game_id)
