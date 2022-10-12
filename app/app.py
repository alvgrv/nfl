import logging
import os

from chalicelib.table import DataTable
from chalicelib.ticker import Ticker
from chalicelib.sitegen import SiteGenerator
from chalicelib.scraper import GameScraperDirector, ScheduleScraper


from chalice import Chalice

app = Chalice(app_name="nfl")

LOGGER = app.log
LOGGER.setLevel(logging.INFO)


@app.schedule("rate(2 hours)")
def ticker_function(_event):
    """Cron function checking for new data at source."""
    command = Ticker(DataTable(), ScheduleScraper(ScheduleScraper.get_current_season()))
    command.run()


@app.lambda_function()
def manual_ticker_function(_event, _context):
    """Cron function checking for new data at source."""
    command = Ticker(DataTable(), ScheduleScraper(ScheduleScraper.get_current_season()))
    command.run()


@app.on_cw_event({"detail-type": ["game_to_scrape"]})
def scraper_function(event):
    """Event-driven scraper, takes one game_id."""
    command = GameScraperDirector(event, DataTable())
    command.run()


@app.on_dynamodb_record(os.environ["DATA_TABLE_STREAM"])
def site_gen_function(_event):
    command = SiteGenerator(DataTable())
    command.run()
