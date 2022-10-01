import logging
import os

from chalicelib.dbinitlib import DatabaseInit
from chalicelib.tickerlib import Ticker
from chalicelib.sitegenlib import SiteGenerator
from chalicelib.scraperlib import EventScraper
from chalicelib.utils import (
    get_dynamodb_table,
)
from chalice import Chalice

app = Chalice(app_name="nfl")

LOGGER = app.log
LOGGER.setLevel(logging.INFO)


@app.schedule("cron(0 0 1 7 *)")
def db_init_function():
    dbinit = DatabaseInit()
    dbinit.run()


@app.lambda_function()
def manual_db_init_function():
    dbinit = DatabaseInit()
    dbinit.run()


@app.schedule("rate(2 hours)")
def ticker_function(_event):
    """Cron function checking for new data at source."""
    ticker = Ticker()
    ticker.run()


@app.lambda_function()
def manual_ticker_function():
    ticker = Ticker()
    ticker.run()


@app.schedule("rate(2 hours)")
@app.on_cw_event({"detail-type": ["game_to_scrape"]})
def scraper_function(event):
    """Event-driven scraper, takes one game_id."""
    game_event_scraper = EventScraper(event)
    game_event_scraper.run()


@app.on_dynamodb_record(os.environ["DATA_TABLE_STREAM"])
def site_gen_function(_event):
    site_generator = SiteGenerator()
    site_generator.run()
