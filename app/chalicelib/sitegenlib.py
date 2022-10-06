import boto3

from .utils import get_current_season, get_dynamodb_table, page_template_string
import os
from jinja2 import Environment as JinjaEnv


class SiteGenerator:
    def __init__(self):
        self.schedule_table = get_dynamodb_table(os.environ["SCHEDULE_TABLE"])
        self.schedule_table_query = self.schedule_table.scan()
        self.schedule_table_results = self.schedule_table_query["Items"]
        self.data_table = get_dynamodb_table(os.environ["DATA_TABLE"])
        self.data_table_query = self.data_table.scan()
        self.data_table_results = self.data_table_query["Items"]

    @property
    def weeks_with_data(self):
        # TODO type casting is a mess all over
        return set(
            int(d["week"])
            for d in self.schedule_table_results
            if all([d["has_data"] is True, d["season"] == str(get_current_season())])
        )

    @property
    def current_week(self):
        return max([int(s) for s in self.weeks_with_data])

    @property
    def previous_week(self):
        if self.current_week == 1:
            return max(
                int(d["week"])
                for d in self.data_table_results
                if all(
                    [
                        d["has_data"] is True,
                        d["season"] == str(get_current_season() - 1),
                    ]
                )
            )

        return self.current_week - 1

    @property
    def page_template(self):
        env = JinjaEnv()
        return env.from_string(page_template_string)

    @property
    def current_week_html(self):
        current_week_games = [
            d for d in self.data_table_results if d["week"] == str(self.current_week)
        ]
        sorted(current_week_games, key=lambda d: d["fun_index"], reverse=True)
        return self.page_template.render(games=current_week_games)

    @property
    def previous_week_html(self):
        previous_week_games = [
            d for d in self.data_table_results if d["week"] == str(self.previous_week)
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

        LOGGER.info("Generating previous week %s", self.previous_week)
        with open("/tmp/previous.html", "w+") as file:
            file.write(self.previous_week_html)
        self.site_bucket.upload_file("/tmp/previous.html", "previous.html")
