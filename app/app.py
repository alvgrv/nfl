import logging
import json
import os

from chalicelib.scraper import GameScraper
from chalicelib.utils import (
    add_dict_to_dynamodb,
    get_dynamodb_table,
    populate_empty_schedule,
    new_seasons_at_source,
    get_game_ids_to_scrape,
    put_onto_eventbridge,
    scrape_season_schedule_into_db,
)

from chalice import Chalice
import boto3

app = Chalice(app_name="app")

LOGGER = app.log
LOGGER.setLevel(logging.INFO)

# @app.schedule("rate(10 minutes)") TODO
@app.lambda_function()
def ticker(_event, _context):
    """Cron function checking for new data."""
    LOGGER.info("Connecting to schedule table")
    schedule_table = get_dynamodb_table(os.environ["SCHEDULE_TABLE"])

    if not len(schedule_table.scan()["Items"]):
        LOGGER.info("Schedule table empty, populating...")
        populate_empty_schedule(schedule_table)

    LOGGER.info("Checking years up to date...")
    if new_seasons_at_source(schedule_table):
        LOGGER.info("New season(s) found at source")
        for season in new_seasons_at_source(schedule_table):
            LOGGER.info("Scraping season %s schedule...", season)
            scrape_season_schedule_into_db(season, schedule_table)

    LOGGER.info("Checking new games to scrape...")
    # game_ids_to_scrape = get_game_ids_to_scrape(schedule_table) TODO
    game_ids_to_scrape = ["202209080ram"]
    if game_ids_to_scrape:
        LOGGER.info(
            "%s new games found to scrape, putting onto EventBridge...",
            len(game_ids_to_scrape),
        )
        eb = boto3.client("events")
        put_onto_eventbridge(game_ids_to_scrape, eb)

    LOGGER.info("Ticker checks complete")

    return None


@app.on_cw_event({"detail-type": ["game_to_scrape"]})
def scraper(event):
    game_id = event.to_dict()["detail"]["game_id"]
    game_scraper = GameScraper(game_id)
    game_dict = game_scraper.game_dict
    data_table = get_dynamodb_table(os.environ["DATA_TABLE"])
    add_dict_to_dynamodb(game_dict, data_table)


# scraper does not have perms to put item on DDB
# but it should do
