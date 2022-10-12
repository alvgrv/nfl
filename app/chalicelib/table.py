import os

import boto3


class DataTable:
    def __init__(self):
        self.ddb = boto3.resource("dynamodb")
        self.name = os.environ["DATA_TABLE"]
        self.table = self.ddb.Table(self.name)

    def single_column_as_list(self, column):
        list_of_dicts = self.table.scan(AttributesToGet=list([column]))["Items"]
        return sorted([d[column] for d in list_of_dicts])

    @property
    def game_ids(self):
        return self.single_column_as_list("id")

    @property
    def weeks(self):
        return self.single_column_as_list("week")

    @property
    def seasons(self):
        return self.single_column_as_list("season")

    @property
    def all_rows(self):
        """returns list of dicts"""
        return self.table.scan()["Items"]
