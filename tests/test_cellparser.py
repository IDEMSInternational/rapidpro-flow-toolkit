import unittest
from typing import List

from rpft.parsers.common.cellparser import CellParser
from rpft.parsers.common.rowparser import ParserModel


class InnerModel(ParserModel):
    str_field: str

class OuterModel(ParserModel):
    inner: InnerModel
    strings: List[str]


class TestStringSplitter(unittest.TestCase):

    def setUp(self):
        self.parser = CellParser()

    def compare_split_by_separator(self, string, exp):
        out = self.parser.split_by_separator(string, '|')
        self.assertEqual(out, exp)

    def compare_cleanse(self, string, exp):
        out = self.parser.cleanse(string)
        self.assertEqual(out, exp)

    def compare_split_into_lists(self, string, exp):
        out = self.parser.split_into_lists(string)
        self.assertEqual(out, exp)

    def test_split_by_separator(self):
        self.compare_split_by_separator('a', 'a')
        self.compare_split_by_separator('a|b', ['a', 'b'])
        self.compare_split_by_separator('a|b|', ['a', 'b'])
        self.compare_split_by_separator('a|', ['a'])
        self.compare_split_by_separator('a\\|', 'a\\|')

    def test_cleanse(self):
        self.compare_cleanse('a', 'a')
        self.compare_cleanse('a\\|', 'a|')
        self.compare_cleanse('a\\;', 'a;')
        self.compare_cleanse('a\\\\', 'a\\')
        self.compare_cleanse('a\\\\;', 'a\\;')
        self.compare_cleanse([[['a\\;']]], [[['a;']]])
        self.compare_cleanse(['\\\\', '\\;'], ['\\', ';'])

    def test_split_into_lists(self):
        self.compare_split_into_lists('1', '1')
        self.compare_split_into_lists('1;', ['1'])
        self.compare_split_into_lists('1;2', ['1','2'])
        self.compare_split_into_lists('1;2;', ['1','2'])
        self.compare_split_into_lists('1;2;;', ['1','2',''])
        self.compare_split_into_lists('1;2|', [['1','2']])
        self.compare_split_into_lists('1;|2;', [['1'],['2']])
        self.compare_split_into_lists('1;|2', [['1'],'2'])
        self.compare_split_into_lists('|a', ['', 'a'])
        self.compare_split_into_lists('a|b', ['a', 'b'])
        self.compare_split_into_lists('a|b|', ['a', 'b'])
        self.compare_split_into_lists('a|', ['a'])
        self.compare_split_into_lists('a\\|', 'a|')
        self.compare_split_into_lists('a\\;', 'a;')
        self.compare_split_into_lists('a|\\;', ['a', ';'])
        self.compare_split_into_lists('a|;', ['a', ['']])
        self.compare_split_into_lists('1;2|3;4', [['1', '2'], ['3', '4']])
        self.compare_split_into_lists('1;2|3;4;', [['1', '2'], ['3', '4']])
        self.compare_split_into_lists('1;2|3;4\\;', [['1', '2'], ['3', '4;']])
        self.compare_split_into_lists('1;2|3;4\\|', [['1', '2'], ['3', '4|']])
        self.compare_split_into_lists(CellParser.escape_string('|;;|\\;\\\\\\|'), '|;;|\\;\\\\\\|')

    def test_string_stripping(self):
        self.compare_cleanse(' a;\n', 'a;')
        self.compare_cleanse([' a;\n'], ['a;'])
        self.compare_split_into_lists(' a\n|\nb ', ['a', 'b'])
        self.compare_split_into_lists('1; 2\n|\n3; 4', [['1', '2'], ['3', '4']])


class TestCellParser(unittest.TestCase):

    def setUp(self):
        self.parser = CellParser()

    def test_parse_as_string(self):
        out = self.parser.parse_as_string('plain string')
        self.assertEqual(out, 'plain string')
        out = self.parser.parse_as_string('{{var}} :)', context={'var' : 15})
        self.assertEqual(out, '15 :)')

        instance = OuterModel(strings=['a', 'b'], inner=InnerModel(str_field='xyz'))
        context = {'instance' : instance}
        out = self.parser.parse_as_string('{{instance.strings[1]}}', context=context)
        self.assertEqual(out, 'b')
        out = self.parser.parse_as_string('{{instance.inner.str_field}}', context=context)
        self.assertEqual(out, 'xyz')

    def test_parse(self):
        out = self.parser.parse('a;b;c')
        self.assertEqual(out, ['a', 'b', 'c'])

        context = {'list' : ['a', 'b', 'c']}
        out = self.parser.parse('{% for e in list %}{{e}}{% endfor %}', context=context)
        self.assertEqual(out, 'abc')
        # Templating comes first, only then splitting into a list
        out = self.parser.parse('{% for e in list %}{{e}};{% endfor %}', context=context)
        self.assertEqual(out, ['a', 'b', 'c'])

    def test_escape_filter(self):
        out = self.parser.parse('{{"a;b;c"}}')
        self.assertEqual(out, ['a', 'b', 'c'])
        out = self.parser.parse('{{"a;b;c"|escape}}')
        self.assertEqual(out, 'a;b;c')
        string = '\\|;\\'
        out = self.parser.parse('{{string|escape}}', context={'string':string})
        self.assertEqual(out, string)

    def test_parse_native_tpye(self):
        out = self.parser.parse_as_string('{@(1,2,[3,"a"])@}')
        self.assertEqual(out, (1,2,[3,'a']))
        out = self.parser.parse_as_string('  {@(1,2,[3,"a"])@} ')
        self.assertEqual(out, (1,2,[3,'a']))
        out = self.parser.parse_as_string('{@ ( 1 , 2 , [ 3 , "a" ] ) @}')
        self.assertEqual(out, (1,2,[3,'a']))

        instance = OuterModel(strings=['a', 'b'], inner=InnerModel(str_field='xyz'))
        context = {'instance' : instance}
        out = self.parser.parse_as_string('{@instance@}', context=context)
        self.assertEqual(out, instance)
        out = self.parser.parse_as_string('{@instance.inner@}', context=context)
        self.assertEqual(out, instance.inner)
        out = self.parser.parse_as_string('{@instance.strings@}', context=context)
        self.assertEqual(out, ['a', 'b'])

        class TestObj:
            def __init__(self, value):
                self.value = value
        test_objs = [TestObj('1'), TestObj('2'), TestObj('A')]
        out = self.parser.parse_as_string('{@test_objs@}', context={'test_objs' : test_objs})
        self.assertEqual(out, test_objs)
        out = self.parser.parse_as_string('{@range(1,5)@}')
        self.assertEqual(out, range(1,5))
