import boto3

from . import LOGGER
from .table import DataTable
from .utils import page_template_string
import os
from jinja2 import Environment as JinjaEnv


class SiteGenerator:
    def __init__(self, data_table: DataTable):
        self.data_table = data_table

    @property
    def current_week(self):
        return max(map(lambda x: int(x), self.data_table.weeks))

    @property
    def previous_week(self):
        return self.current_week - 1

    @property
    def page_template(self):
        env = JinjaEnv()
        return env.from_string(page_template_string)

    @property
    def current_week_html(self):
        current_week_games = [
            g for g in self.data_table.all_rows if g["week"] == self.current_week
        ]
        sorted(current_week_games, key=lambda d: d["fun_index"], reverse=True)
        return self.page_template.render(games=current_week_games)

    @property
    def previous_week_html(self):
        previous_week_games = [
            d for d in self.data_table.weeks if int(d["week"]) == self.previous_week
        ]
        sorted(previous_week_games, key=lambda d: d["fun_index"], reverse=True)
        return self.page_template.render(games=previous_week_games)

    @property
    def site_bucket(self):
        s3 = boto3.resource("s3")
        return s3.Bucket(os.environ["SITE_BUCKET_NAME"])

    def run(self):
        LOGGER.info("Event received")

        LOGGER.info("Generating current week %s", self.current_week)
        with open("/tmp/current.html", "w+") as file:
            file.write(self.current_week_html)
        self.site_bucket.upload_file("/tmp/current.html", "current.html")

        if self.previous_week:
            LOGGER.info("Generating previous week %s", self.previous_week)
            with open("/tmp/previous.html", "w+") as file:
                file.write(self.previous_week_html)
            self.site_bucket.upload_file("/tmp/previous.html", "previous.html")
        else:
            self.site_bucket.delete_objects(
                Delete={"Objects": [{"Key": "previous.html"}]}
            )
