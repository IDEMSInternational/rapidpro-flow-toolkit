import unittest
import json
from collections import OrderedDict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Dict, Optional

from rpft.parsers.common.rowdatasheet import RowDataSheet
from tests.mocks import MockRowParser


rowA = OrderedDict([
    ('str_field', 'main string A'),
    ('list_str:0', 'a'),
    ('list_str:1', 'b'),
    ('model_default:int_field', 5),
])

rowB = OrderedDict([
    ('str_field', 'main string B'),
    ('2nd_field', '2nd field'),
    ('list_str:0', 'A'),
])

rowC = OrderedDict([
    ('model_default:int_field', 15),
    ('x:y:z', 'x y z'),
])

rowD = OrderedDict()

rowCycle = OrderedDict([
    ('list_str:0', '1'),
    ('str_field', 'main string Cycle'),
])

headersABCD_exp = [
    'str_field',
    '2nd_field',
    'list_str:0',
    'list_str:1',
    'model_default:int_field',
    'x:y:z',
]

contentABCD_exp = [
    ('main string A', '', 'a', 'b', 5, ''),
    ('main string B', '2nd field', 'A', '', '', ''),
    ('', '', '', '', 15, 'x y z'),
    ('', '', '', '', '', ''),
]

headersAC_exp = [
    'str_field',
    'list_str:0',
    'list_str:1',
    'model_default:int_field',
    'x:y:z',
]

contentAC_exp = [
    ('main string A', 'a', 'b', 5, ''),
    ('', '', '', 15, 'x y z'),
]

class TestRowDataSheet(unittest.TestCase):

    def setUp(self):
        self.rowparser = MockRowParser()

    def compare_headers(self, rows, headers_exp):
        sheet = RowDataSheet(self.rowparser, rows)
        headers = sheet._get_headers()
        self.assertEqual(headers, headers_exp)

    def compare_tablibs(self, rows, output_exp):
        sheet = RowDataSheet(self.rowparser, rows)
        output = sheet.convert_to_tablib()
        for i, row in enumerate(output):
            self.assertEqual(row, output_exp[i])

    def test_get_headers_ABCD(self):
        self.compare_headers([rowA, rowB, rowC, rowD], headersABCD_exp)

    def test_get_headers_AC(self):
        self.compare_headers([rowA, rowC], headersAC_exp)

    def test_get_headers_cycle(self):
        with self.assertRaises(ValueError):
            sheet = RowDataSheet(self.rowparser, [rowA, rowCycle])
            headers = sheet._get_headers()

    def test_to_tablib_ABCD(self):
        self.compare_tablibs([rowA, rowB, rowC, rowD], contentABCD_exp)

    def test_to_tablib_AC(self):
        self.compare_tablibs([rowA, rowC], contentAC_exp)

    def test_export_csv(self):
        # Not our job to test the contents (tablib's responsibility),
        # but we want to make sure here the export function works.
        with TemporaryDirectory() as outdir:
            outfile = Path(outdir) / "export.csv"
            RowDataSheet(
                self.rowparser, [rowA, rowC]
            ).export(outfile)

    def test_export_xlsx(self):
        # Not our job to test the contents (tablib's responsibility),
        # but we want to make sure here the export function works.
        with TemporaryDirectory() as outdir:
            outfile = Path(outdir) / "export.xlsx"
            RowDataSheet(
                self.rowparser, [rowA, rowC]
            ).export(outfile, file_format='xlsx')


if __name__ == '__main__':
    unittest.main()
