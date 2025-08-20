from unittest import TestCase

from benedict import benedict
from rpft.parsers.common.rowparser import ParserModel
from rpft.sources import JSONDataSource


class TestModel(ParserModel):
    k1: str


class TestJSONDataSource(TestCase):

    def setUp(self):
        self.source = JSONDataSource([])

    def test_get_retrieves_by_key(self):
        data = {"o1": [{"k1": "v1"}]}
        self.source.objs = [(data, "data")]
        item = self.source.get("o1")

        self.assertEqual(item, ([{"k1": "v1"}], "data", "o1"))
        self.assertEqual(type(item[0][0]), benedict)

    def test_get_retrieves_by_key_and_model(self):
        data = {"o1": [{"k1": "v1"}]}
        self.source.objs = [(data, "data")]
        item = self.source.get("o1", TestModel)

        self.assertEqual(item, ([TestModel(k1="v1")], "data", "o1"))
        self.assertEqual(type(item[0][0]), TestModel)

    def test_get_retrieves_last_duplicated_item(self):
        item1 = {"o1": [{"k1": "v1"}]}
        item2 = {"o1": [{"k1": "v2"}]}
        self.source.objs = [(item1, "item1"), (item2, "item2")]
        fetched = self.source.get("o1")

        self.assertEqual(fetched, (item2["o1"], "item2", "o1"))

    def test_raise_error_when_item_missing(self):
        self.assertRaises(Exception, self.source.get, "o1")

    def test_get_all_concatenates_items_with_same_key(self):
        item1 = {"o1": [{"k1": "v1"}]}
        item2 = {"o1": [{"k1": "v2"}]}
        self.source.objs = [(item1, "item1"), (item2, "item2")]
        fetched = self.source.get_all("o1")

        self.assertEqual(
            fetched,
            [
                ([{"k1": "v1"}], "item1", "o1"),
                ([{"k1": "v2"}], "item2", "o1"),
            ],
        )


class TestLegacySheetBasedRetrieval(TestCase):

    def test_get_sheet_by_name(self):
        source = JSONDataSource([])
        source.objs = [({"o1": [{"k1": "v1"}]}, "data")]
        sheet = source._get_sheet_or_die("o1")

        self.assertEqual(sheet.name, "data")
        self.assertEqual(sheet.table.headers, ["k1"])
        self.assertEqual(sheet.table[0], ("v1",))
