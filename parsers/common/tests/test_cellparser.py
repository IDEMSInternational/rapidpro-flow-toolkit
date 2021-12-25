import unittest

from parsers.common.cellparser import get_object_from_cell_value, get_separators


class TestCellParser(unittest.TestCase):

    def test_get_object_from_cell_value(self):
        obj = get_object_from_cell_value('condition;a|condition_type;has_any_word|condition_name;A')
        self.assertDictEqual(
            {'condition': 'a', 'condition_type': 'has_any_word', 'condition_name': 'A'},
            obj)

    def test_get_separators(self):
        s_1, s_2, s_3 = get_separators('|;::;|')
        self.assertEqual('|', s_1)
        self.assertEqual(';', s_2)
        self.assertEqual(':', s_3)

        s_1, s_2, s_3 = get_separators('|;|;|')
        self.assertEqual('|', s_1)
        self.assertEqual(';', s_2)
        self.assertIsNone(s_3)

        s_1, s_2, s_3 = get_separators('|:|:|')
        self.assertEqual('|', s_1)
        self.assertEqual(':', s_2)
        self.assertIsNone(s_3)

        s_1, s_2, s_3 = get_separators(';:;:')
        self.assertEqual(';', s_1)
        self.assertEqual(':', s_2)
        self.assertIsNone(s_3)
