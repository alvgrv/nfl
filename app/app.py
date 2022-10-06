import logging
import os

from chalicelib.dbinitlib import DatabaseInit
from chalicelib.tickerlib import Ticker
from chalicelib.sitegenlib import SiteGenerator
from chalicelib.scraperlib import GameEventScraper, GameScraper
from chalicelib.utils import (
    get_dynamodb_table,
)
from chalice import Chalice

app = Chalice(app_name="nfl")

LOGGER = app.log
LOGGER.setLevel(logging.INFO)


@app.schedule("cron(0 0 1 7 ? *)")  # min hour dom mth dow year
def db_init_function(_event):
    command = DatabaseInit()
    command.run()
    return {"status": "success"}


@app.lambda_function()
def manual_db_init_function(_event, _context):
    command = DatabaseInit()
    command.run()
    return {"status": "success"}


@app.schedule("rate(2 hours)")
def ticker_function(_event):
    """Cron function checking for new data at source."""
    command = Ticker()
    command.run()


@app.lambda_function()
def manual_ticker_function(_event, _context):
    command = Ticker()
    command.run()


@app.on_cw_event({"detail-type": ["game_to_scrape"]})
def scraper_function(event):
    """Event-driven scraper, takes one game_id."""
    command = GameEventScraper(event)
    command.run()


@app.on_dynamodb_record(os.environ["DATA_TABLE_STREAM"])
def site_gen_function(_event):
    command = SiteGenerator()
    command.run()
