import os

import boto3


class DataTable:
    def __init__(self):
        self.ddb = boto3.resource("dynamodb")
        self.name = os.environ["DATA_TABLE"]
        self.table = self.ddb.Table(self.name)

    @staticmethod
    def scan_for_attributes(self, *args):
        return self.table.scan(AttributesToGet=list(args))["Items"]

    @property
    def match_ids(self):
        return self.scan_for_attributes("match_id")

    @property
    def seasons(self):
        return self.scan_for_attributes("season")

    @property
    def all_rows(self):
        return self.table.scan()["Items"]
