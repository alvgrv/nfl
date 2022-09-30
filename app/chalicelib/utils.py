import datetime as dt
from . import LOGGER
import json

import boto3

from .scraperlib import ScheduleScraper


def get_dynamodb_table(table_name):
    ddb = boto3.resource("dynamodb")
    return ddb.Table(table_name)


def get_current_season():
    """Returns int"""
    if dt.datetime.now().month >= 7:
        return dt.datetime.now().year
    return dt.datetime.now().year - 1


def add_dict_to_dynamodb(dict_, table):
    table.put_item(Item=dict_)


def scrape_season_schedule_into_db(season, table):
    LOGGER.info("Scraping season %s", season)
    schedule_scraper = ScheduleScraper(season)
    schedule_df = schedule_scraper.season_schedule
    with table.batch_writer() as batch:
        for _, row in schedule_df.iterrows():
            batch.put_item(Item=row.to_dict())
    LOGGER.info("Season %s scraped into database", season)


def populate_empty_schedule(table, back_seasons=0):
    current_season = get_current_season()
    seasons = [current_season]
    if back_seasons:
        seasons.extend([current_season - n for n in range(seasons + 1)])
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


def put_onto_eventbridge(source, detail, detail_type):
    """Put an event onto EventBridge.

    Args:
        source (str): source
        detail (dict): detail as dict
        detail_type (str): detail type

    """
    eb = boto3.client("events")
    response = eb.put_events(
        Entries=[
            {
                "Source": source,
                "Detail": json.dumps(detail),
                "DetailType": detail_type,
            }
        ]
    )
    if response["FailedEntryCount"]:
        LOGGER.info("Event put failed")
    LOGGER.info("Event put onto EventBridge")


page_template_string = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Fun Index</title>
    <link rel="shortcut icon" href="static/favicon.ico">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.1/dist/css/bootstrap.min.css" rel="stylesheet"
        integrity="sha384-iYQeCzEYFbKjA/T2uDLTpkwGzCiq6soy8tYaI1GyVh/UjpbCx/TYkiZhlZB6+fzT" crossorigin="anonymous">

    <style>
        @media screen and (max-width: 576px) {

            table {
                /* override Bootstrap width */
                width: inherit !important;
            }

            td,
            th {
                width: auto;
            }

            td.min,
            th.min {
                width: 1% !important;
                white-space: nowrap !important;
            }

            p {
                font-size: 0.9rem !important;
            }


            th,
            tr,
            td {
                font-size: 0.75rem !important;
            }
        }

        p.footer,
        p.text,
        p.blurb {
            text-align: center;
        }
    </style>

</head>

<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">NFL Fun Index</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
                aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/previous">Last week</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <br>

    <div class="container">
        <div class="row justify-content-center">
            <div class="col">
            </div>
            <div class="col-9-sm">
                <p class='text'>We crunch the numbers and rate games on how fun they were to watch, so you can catch up
                    later without
                    ruining
                    the
                    final score
                </p>
            </div>
            <div class="col">
            </div>
        </div>



        <div class="row justify-content-center">
            <div class="col">
            </div>
            <div class="col-9-sm">
                <br>
                <table class="table table-striped">
                    <tr>
                        <th class='min'>Week</th>
                        <th class='min'>Date</th>
                        <th>Time</th>
                        <th>Away Team</th>
                        <th>Home Team</th>
                        <th class='min'>Fun Index</th>
                    </tr>
                    {% for game in games %}
                    <tr>
                        <td class='min'>{{ game.week }}</td>
                        <td class='min'>{{ game.date }}</td>
                        <td class='min'>{{ game.time }}</td>
                        <td>{{ game.away_team }}</td>
                        <td>{{ game.home_team }}</td>
                        <td class='min'>{{ game.fun_index }}</td>
                    </tr>
                    {% endfor %}
                </table>


                <br><br><br>
                <!-- <p class="footer">
                    Made by <a href="http://github.com/elgrove">elgrove</a>
                </p> -->
            </div>
            <div class="col">
            </div>
        </div>

        <br>

    </div>





    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.1/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-u1OknCvxWvY5kfmNBILK2hRnQC3Pr17a+RTT6rIHI7NnikvbZlHgTPOOmMi466C8"
        crossorigin="anonymous"></script>

</body>

</html>
"""
