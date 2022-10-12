"""Site generator function."""
import os

import boto3
from jinja2 import Environment as JinjaEnv

from . import LOGGER
from .table import DataTable
from .page_html import PAGE_TEMPLATE_STRING


class SiteGenerator:
    """Event-driven function to generate web pages from data.

    Args:
        data_table (DataTable): instance of data table class

    """

    def __init__(self, data_table: DataTable):
        """Instantiate the class with dependency injection of DataTable."""
        self.data_table = data_table

    @property
    def current_week(self):
        """Return the highest week number in the data table."""
        return max(int, self.data_table.weeks)

    @property
    def previous_week(self):
        """Return the previous week number in the data table."""
        return self.current_week - 1

    @property
    def page_template(self):
        """Return a Jinja template based on the template html string."""
        env = JinjaEnv()
        return env.from_string(PAGE_TEMPLATE_STRING)

    @property
    def current_week_html(self):
        """Return web page html string for the current week's game"""
        current_week_games = [
            g for g in self.data_table.all_rows if g["week"] == self.current_week
        ]
        sorted(current_week_games, key=lambda d: d["fun_index"], reverse=True)
        return self.page_template.render(games=current_week_games)

    @property
    def previous_week_html(self):
        """Return web page html string for the previous week's games."""
        previous_week_games = [
            d for d in self.data_table.weeks if int(d["week"]) == self.previous_week
        ]
        sorted(previous_week_games, key=lambda d: d["fun_index"], reverse=True)
        return self.page_template.render(games=previous_week_games)

    @property
    def site_bucket(self):
        """Return the boto3 s3 Bucket object for the web page html files."""
        s3 = boto3.resource("s3")
        return s3.Bucket(os.environ["SITE_BUCKET_NAME"])

    def run(self):
        """Execute the command.

        Generate current week html and put to s3 bucket

        If current week == 1 and previous week == 0, delete previous html page
        Else generate previous week html and put to s3 bucket

        """
        LOGGER.info("Event received")

        LOGGER.info("Generating current week %s", self.current_week)
        with open("/tmp/current.html", "w+", encoding="utf-8") as file:
            file.write(self.current_week_html)
        self.site_bucket.upload_file("/tmp/current.html", "current.html")

        if self.previous_week:
            LOGGER.info("Generating previous week %s", self.previous_week)
            with open("/tmp/previous.html", "w+", encoding="utf-8") as file:
                file.write(self.previous_week_html)
            self.site_bucket.upload_file("/tmp/previous.html", "previous.html")
        else:
            self.site_bucket.delete_objects(
                Delete={"Objects": [{"Key": "previous.html"}]}
            )
