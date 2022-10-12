"""Module wrapping a dynamodb table."""

import os

import boto3


class DataTable:
    """Class for dealing with dynamodb data table."""

    def __init__(self):
        """Instantiate the class."""
        self.ddb = boto3.resource("dynamodb")
        self.name = os.environ["DATA_TABLE"]
        self.table = self.ddb.Table(self.name)

    def single_column_as_list(self, column):
        """Return the values of a single column in table as a sorted list."""
        list_of_dicts = self.table.scan(AttributesToGet=list([column]))["Items"]
        return sorted([d[column] for d in list_of_dicts])

    @property
    def game_ids(self):
        """Return list containing all game_ids in table."""
        return self.single_column_as_list("id")

    @property
    def weeks(self):
        """Return a list containing all unique week numbers in table as strings."""
        return self.single_column_as_list("week")

    @property
    def seasons(self):
        """Return a list containing all unique season numbers in table as strings."""
        return self.single_column_as_list("season")

    @property
    def all_rows(self):
        """Return list of dicts containing every item in the table."""
        return self.table.scan()["Items"]
