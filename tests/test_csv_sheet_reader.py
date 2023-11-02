from unittest import TestCase

from rpft.parsers.sheets import CSVSheetReader, SheetReaderError
from tests import TESTS_ROOT


class TestCsvSheetReader(TestCase):
    def setUp(self):
        self.source = str(TESTS_ROOT / "input/example1/csv_workbook")
        self.reader = CSVSheetReader(path=self.source)

    def test_access_main_sheet(self):
        self.assertEqual(
            self.reader.main_sheet.data[3],
            ("data_sheet", "nesteddata", "", "", "", "NestedRowModel", "", "", "", ""),
        )

    def test_access_existing_sheet_by_name(self):
        self.assertEqual(
            self.reader.get_sheet("my_basic_flow").data[0],
            ("", "send_message", "start", "Some text"),
        )

    def test_access_missing_sheet(self):
        self.assertIsNone(self.reader.get_sheet("missing"))

    def test_main_sheet_must_exist(self):
        with self.assertRaises(SheetReaderError):
            CSVSheetReader(self.source, "missing")
