import json
from unittest import TestCase

from tablib import Dataset

from rpft.converters import to_json
from rpft.parsers.sheets import AbstractSheetReader, Sheet


class TestReaderToJson(TestCase):
    def test_something(self):
        reader = MockSheetReader(
            {
                "sheet1": Sheet(
                    reader=None,
                    name="sheet1",
                    table=Dataset(
                        ("row1_col1", "row1_col2", "row1_col3"),
                        headers=["col1", "col2", "col3"],
                    ),
                ),
                "sheet2": Sheet(
                    reader=None,
                    name="sheet2",
                    table=Dataset(
                        ("row1_col1", "row1_col2", "row1_col3"),
                        headers=["col1", "col2", "col3"],
                    ),
                ),
            }
        )
        self.assertDictEqual(
            json.loads(to_json(reader)),
            {
                "meta": {
                    "version": "0.1.0",
                },
                "sheets": {
                    "sheet1": [
                        {
                            "col1": "row1_col1",
                            "col2": "row1_col2",
                            "col3": "row1_col3",
                        },
                    ],
                    "sheet2": [
                        {
                            "col1": "row1_col1",
                            "col2": "row1_col2",
                            "col3": "row1_col3",
                        },
                    ],
                },
            },
        )


class MockSheetReader(AbstractSheetReader):
    def __init__(self, sheets):
        self._sheets = sheets
