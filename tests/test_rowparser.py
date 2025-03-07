import unittest
from typing import List

from rpft.parsers.common.rowparser import ParserModel, RowParser
from tests.mocks import MockCellParser


class SubModel(ParserModel):
    str_field: str = ""
    list_field: list = []


class MyModel(ParserModel):
    bool_field: int = False
    int_field: int = 0
    str_field: str = ""
    list_field: list = []
    submodel_field: SubModel = SubModel()


class BoolModel(ParserModel):
    bool_field: bool = True


class TestRowParserBoolean(unittest.TestCase):
    def setUp(self):
        self.parser = RowParser(BoolModel, MockCellParser())
        self.falseModel = BoolModel(**{"bool_field": False})
        self.trueModel = BoolModel(**{"bool_field": True})

    def test_convert_false(self):
        inputs = [
            {"bool_field": "False"},
            {"bool_field": "  False  "},
            {"bool_field": "FALSE"},
            {"bool_field": "false"},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.falseModel)

    def test_convert_true(self):
        inputs = [
            {"bool_field": "True"},
            {"bool_field": "  True  "},
            {"bool_field": "TRUE"},
            {"bool_field": "true"},
            {"bool_field": "something"},
            {"bool_field": "1"},
            {"bool_field": "0"},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.trueModel)

    def test_convert_default(self):
        inp = {}
        out = self.parser.parse_row(inp)
        self.assertEqual(out, self.trueModel)


class IntModel(ParserModel):
    int_field: int = 0


class TestRowParserInt(unittest.TestCase):
    def setUp(self):
        self.parser = RowParser(IntModel, MockCellParser())
        self.twelveModel = IntModel(**{"int_field": 12})
        self.zeroModel = IntModel(**{"int_field": 0})

    def test_convert_int(self):
        inputs = [
            {"int_field": "12"},
            {"int_field": "  12  "},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.twelveModel)
        inp = {"int_field": "twelve"}
        with self.assertRaises(ValueError):
            out = self.parser.parse_row(inp)

    def test_convert_default(self):
        inp = {}
        out = self.parser.parse_row(inp)
        self.assertEqual(out, self.zeroModel)


class ListStrModel(ParserModel):
    list_field: List[str] = []


class TestRowParserListStr(unittest.TestCase):
    def setUp(self):
        self.parser = RowParser(ListStrModel, MockCellParser())
        self.emptyModel = ListStrModel(**{"list_field": []})
        self.oneModel = ListStrModel(**{"list_field": ["1"]})
        self.onetwoModel = ListStrModel(**{"list_field": ["1", "2"]})

    def test_convert_empty(self):
        inputs = [
            {},
            # {"list_field": ""},
            {"list_field": []},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.emptyModel)

    def test_convert_single_element(self):
        inputs = [
            {"list_field": ["1"]},
            # {"list_field": ["1", ""]},
            {"list_field": "1"},
            {"list_field.1": "1"},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.oneModel)

    def test_convert_two_element(self):
        inputs = [
            {"list_field": ["1", "2"]},
            {"list_field.1": "1", "list_field.2": "2"},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.onetwoModel)


class ListIntModel(ParserModel):
    list_field: List[int] = []


class TestRowParserListInt(TestRowParserListStr):
    def setUp(self):
        self.parser = RowParser(ListIntModel, MockCellParser())
        self.emptyModel = ListIntModel(**{"list_field": []})
        self.oneModel = ListIntModel(**{"list_field": [1]})
        self.onetwoModel = ListIntModel(**{"list_field": [1, 2]})


class ListModel(ParserModel):
    list_field: list = []


class TestRowParserList(TestRowParserListStr):
    def setUp(self):
        self.parser = RowParser(ListModel, MockCellParser())
        self.emptyModel = ListModel(**{"list_field": []})
        self.oneModel = ListModel(**{"list_field": ["1"]})
        self.onetwoModel = ListModel(**{"list_field": ["1", "2"]})


class DictModel(ParserModel):
    dict_field: dict = {}


class TestRowParserDict(unittest.TestCase):
    def setUp(self):
        self.parser = RowParser(DictModel, MockCellParser())

    def test_convert_empty(self):
        self.emptyModel = DictModel(**{"dict_field": {}})
        inputs = [
            {},
            {"dict_field": ""},
            {"dict_field": []},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.emptyModel)

    def test_convert_single_element(self):
        self.oneModel = DictModel(**{"dict_field": {"K": "V"}})
        inputs = [
            {"dict_field": ["K", "V"]},
            {"dict_field": [["K", "V"]]},
            {"dict_field.K": "V"},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.oneModel)

    def test_convert_two_element(self):
        self.onetwoModel = DictModel(**{"dict_field": {"K1": "V1", "K2": "V2"}})
        inputs = [
            {"dict_field": [["K1", "V1"], ["K2", "V2"]]},
            {"dict_field.K1": "V1", "dict_field.K2": "V2"},
        ]
        for inp in inputs:
            out = self.parser.parse_row(inp)
            self.assertEqual(out, self.onetwoModel)
