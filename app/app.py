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
from jinja2 import Environment as JinjaEnv

app = Chalice(app_name="nfl")

LOGGER = app.log
LOGGER.setLevel(logging.INFO)

SCHEDULE_TABLE = get_dynamodb_table(os.environ["SCHEDULE_TABLE"])
DATA_TABLE = get_dynamodb_table(os.environ["DATA_TABLE"])


@app.schedule("rate(2 hours)")
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
def scraper(event, _context):
    """Event-driven scraper, takes one game_id."""
    game_id = event.to_dict()["detail"]["game_id"]

    LOGGER.info("Event received, scraping game %s", game_id)
    game_scraper = GameScraper(game_id)

    LOGGER.info("Data scraped, putting into DynamoDB")
    add_dict_to_dynamodb(
        game_scraper.game_dict, get_dynamodb_table(os.environ["DATA_TABLE"])
    )

    LOGGER.info("Operation complete")


@app.on_dynamodb_record(os.environ["DATA_TABLE_STREAM"])
def site_gen(event):

    # event_dict = event.to_dict()
    # new_row = event_dict["Records"][0]["dynamodb"]["NewImage"]
    # new_row = {k: v["S"] for k, v in new_row.items()}

    response = SCHEDULE_TABLE.scan()
    weeks_in_data = set(d["week"] for d in response["Items"] if d["has_data"] == True)

    # if new_row['week'] > max(weeks_in_data):
    #     # overwrite previous with current

    # write new current html

    response = DATA_TABLE.scan()
    current_week_games = [
        d
        for d in response["Items"]
        if d["week"] == max(weeks_in_data, key=lambda a: int(a))
    ]

    from chalicelib.utils import page_template_string

    env = JinjaEnv()
    template = env.from_string(page_template_string)
    rendered_html = template.render(games=current_week_games)

    with open("/tmp/current.html", "w+") as file:
        file.write(rendered_html)

    import boto3

    s3 = boto3.resource("s3")
    site_bucket = s3.Bucket(os.environ["SITE_BUCKET_NAME"])
    site_bucket.upload_file("/tmp/current.html", "current.html")
