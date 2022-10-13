"""Entry point for Chalice app."""

import logging
import os

from chalice import Chalice

from chalicelib.table import DataTable
from chalicelib.ticker import Ticker
from chalicelib.sitegen import SiteGenerator
from chalicelib.scraper import GameScraper, GameScraperDirector, ScheduleScraper

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
    """Manually-triggered function checking for new data at source."""
    command = Ticker(DataTable(), ScheduleScraper(ScheduleScraper.get_current_season()))
    command.run()


@app.on_cw_event({"detail-type": ["game_to_scrape"]})
def scraper_function(event):
    """Event-driven scraper, takes one game_id and scrapes that game into the table"""
    game_id = event.to_dict()["detail"]["game_id"]
    command = GameScraperDirector(DataTable(), GameScraper(game_id))
    command.run()


@app.on_dynamodb_record(os.environ["DATA_TABLE_STREAM"])
def site_gen_function(_event):
    """Event-driven site generator, updates html files in S3 on new table row."""
    command = SiteGenerator(DataTable())
    command.run()
