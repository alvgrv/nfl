import logging
import os

from chalicelib.data_table import DataTable
from chalicelib.tickerlib import Ticker
from chalicelib.sitegenlib import SiteGenerator
from chalicelib.scraperlib import GameScraperDirector, ScheduleScraper


from chalice import Chalice

app = Chalice(app_name="nfl")

LOGGER = app.log
LOGGER.setLevel(logging.INFO)


@app.schedule("rate(2 hours)")
def ticker_function(_event):
    """Cron function checking for new data at source."""
    command = Ticker(DataTable(), ScheduleScraper(ScheduleScraper.get_current_season()))
    command.run()


@app.on_cw_event({"detail-type": ["game_to_scrape"]})
def scraper_function(event):
    """Event-driven scraper, takes one game_id."""
    command = GameScraperDirector(event)
    command.run()


@app.on_dynamodb_record(os.environ["DATA_TABLE_STREAM"])
def site_gen_function(_event):
    command = SiteGenerator()
    command.run()
