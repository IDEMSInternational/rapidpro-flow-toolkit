from unittest import TestCase

import tablib
from rpft.parsers.common.sheetparser import SheetParser

from tests.mocks import MockRowParser


class TestSheetParser(TestCase):
    def setUp(self):
        self.parser = SheetParser(
            tablib.Dataset(
                ("row1f1", "row1f2"),
                ("row2f1", "row2f2"),
                ("row3f1", "row3f2"),
                headers=("field1", "field2"),
            ),
            row_parser=MockRowParser(),
        )

    def test_context_and_bookmarks(self):
        self.assertEqual(
            self.parser.parse_next_row(),
            {
                "field1": "row1f1",
                "field2": "row1f2",
                "context": {},
            },
        )

        self.parser.create_bookmark("row2")
        self.parser.add_to_context("key", "value")
        self.assertEqual(
            self.parser.parse_next_row(),
            {
                "field1": "row2f1",
                "field2": "row2f2",
                "context": {"key": "value"},
            },
        )

        self.parser.remove_from_context("key")
        self.assertEqual(
            self.parser.parse_next_row(),
            {
                "field1": "row3f1",
                "field2": "row3f2",
                "context": {},
            },
        )

        self.parser.go_to_bookmark("row2")
        self.assertEqual(
            self.parser.parse_next_row(),
            {
                "field1": "row2f1",
                "field2": "row2f2",
                "context": {},
            },
        )

    def test_parse_all(self):
        rows = self.parser.parse_all()

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            rows[0],
            {
                "field1": "row1f1",
                "field2": "row1f2",
                "context": {},
            },
        )
        self.assertEqual(
            rows[1],
            {
                "field1": "row2f1",
                "field2": "row2f2",
                "context": {},
            },
        )
        self.assertEqual(
            rows[2],
            {
                "field1": "row3f1",
                "field2": "row3f2",
                "context": {},
            },
        )
