import logging
import json
import os

from chalicelib.utils import (
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
    """Cron function checking for new data.

    idempotent first run stuff:
        if table empty
            download calendar for current + last X years
            check have happened and check have data

        else query db for years
            if new year in schedule vs years on site
                download calendar for new year
                check have happened and check have data

    general process:
        get game_id, date, has data from schedule table
        for games not happened but date is in the past:
            if today == game date + 1, check has happened + check has data

        for each game id that has not happened
        if a game has newly happened, update the table
        if a game newly has data, update the table, send an event triggering the scraper
    """
    schedule_table_name = os.environ["SCHEDULE_TABLE"]
    LOGGER.info("Connecting to DynamoDB table %s", schedule_table_name)
    ddb = boto3.resource("dynamodb")
    schedule_table = ddb.Table(schedule_table_name)

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
    game_ids_to_scrape = get_game_ids_to_scrape(schedule_table)
    if game_ids_to_scrape:
        LOGGER.info(
            "%s new games found to scrape, putting onto EventBridge...",
            len(game_ids_to_scrape),
        )
        eb = boto3.client("events")
        put_onto_eventbridge(game_ids_to_scrape, eb)

    LOGGER.info("Ticker checks complete")

    return None


if __name__ == "__main__":
    ticker("", "")


@app.on_cw_event({"detail-type": ["nfl-ticker"]})
def scraper(event, _context):

    print(event)
