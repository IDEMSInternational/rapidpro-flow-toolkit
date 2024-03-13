from unittest import TestCase

from rpft.parsers.sheets import CSVSheetReader, Sheet, XLSXSheetReader, JSONSheetReader
from tests import TESTS_ROOT


class Base:
    class SheetReaderTestCase(TestCase):
        def test_reader_named_correctly(self):
            self.assertEqual(self.reader.name, self.expected_reader_name)

        def test_access_existing_sheet_by_name(self):
            sheet: Sheet = self.reader.get_sheet("my_basic_flow")
            self.assertIsInstance(sheet, Sheet)
            self.assertEqual(sheet.reader, self.reader)
            self.assertEqual(sheet.name, "my_basic_flow")
            self.assertEqual(
                sheet.table[0],
                ("", "send_message", "start", "Some text"),
            )

        def test_access_missing_sheet(self):
            self.assertIsNone(self.reader.get_sheet("missing"))


class TestCsvSheetReader(Base.SheetReaderTestCase):
    def setUp(self):
        path = str(TESTS_ROOT / "input/example1/csv_workbook")
        self.reader = CSVSheetReader(path=path)
        self.expected_reader_name = path


class TestXlsxSheetReader(Base.SheetReaderTestCase):
    def setUp(self):
        filename = str(TESTS_ROOT / "input/example1/content_index.xlsx")
        self.reader = XLSXSheetReader(filename=filename)
        self.expected_reader_name = filename


class TestJsonSheetReader(Base.SheetReaderTestCase):
    def setUp(self):
        filename = str(TESTS_ROOT / "input/example1/content_index.json")
        self.reader = JSONSheetReader(filename=filename)
        self.expected_reader_name = filename
