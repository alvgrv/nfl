import logging
import os

from chalicelib.scraperlib import GameScraper
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

app = Chalice(app_name="nfl")

LOGGER = app.log
LOGGER.setLevel(logging.INFO)

SCHEDULE_TABLE = get_dynamodb_table(os.environ["SCHEDULE_TABLE"])
DATA_TABLE = get_dynamodb_table(os.environ["DATA_TABLE"])

# @app.schedule("rate(1 hour)")
@app.lambda_function()
def ticker(_event, _context):
    """Cron function checking for new data at source."""
    if not len(SCHEDULE_TABLE.scan()["Items"]):
        LOGGER.info("Schedule table empty, populating...")
        populate_empty_schedule(SCHEDULE_TABLE)

    LOGGER.info("Checking years up to date...")
    if new_seasons_at_source(SCHEDULE_TABLE):
        LOGGER.info("New season(s) found at source")
        for season in new_seasons_at_source(SCHEDULE_TABLE):
            LOGGER.info("Scraping season %s schedule...", season)
            scrape_season_schedule_into_db(season, SCHEDULE_TABLE)

    LOGGER.info("Checking new games to scrape...")
    game_ids_to_scrape = get_game_ids_to_scrape(SCHEDULE_TABLE)
    if game_ids_to_scrape:
        LOGGER.info(
            "%s new games found to scrape, putting onto EventBridge...",
            len(game_ids_to_scrape),
        )
        for game_id in game_ids_to_scrape:
            put_onto_eventbridge("nfl-ticker", dict(game_id=game_id), "game_to_scrape")

    LOGGER.info("Ticker checks complete")


@app.on_cw_event({"detail-type": ["game_to_scrape"]})
def scraper(event):
    """Event-driven scraper, takes one game_id."""
    game_id = event.to_dict()["detail"]["game_id"]

    LOGGER.info("Event received, scraping game %s", game_id)
    game_scraper = GameScraper(game_id)

    LOGGER.info("Data scraped, putting into DynamoDB")
    add_dict_to_dynamodb(
        game_scraper.game_dict, get_dynamodb_table(os.environ["DATA_TABLE"])
    )

    LOGGER.info("Operation complete")
