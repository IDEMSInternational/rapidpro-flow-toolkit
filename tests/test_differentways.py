import unittest
import json

from rpft.parsers.common.rowparser import RowParser
from tests.mocks import MockCellParser
from tests.models import FromWrong


output_instance = {
    'row_id': '5',
    'conditions': [
        {'value':'1', 'var':'', 'type':'has_phrase', 'name':'A'},
        {'value':'2', 'var':'', 'type':'has_phrase', 'name':'B'},
        {'value':'3', 'var':'', 'type':'has_phrase', 'name':''},
    ]
}

input1 = {
    'row_id': '5',
    'conditions.*.value' : ['1', '2', '3'],
    'conditions.*.var' : '',
    'conditions.*.type' : ['has_phrase', 'has_phrase', 'has_phrase'],
    'conditions.*.name' : ['A','B',''],
}

input2 = {
    'row_id': '5',
    'conditions.*.value' : ['1', '2', '3'],
    'conditions.*.var' : '',
    'conditions.*.type' : ['has_phrase', 'has_phrase', 'has_phrase'],
    'conditions.*.name' : ['A','B'],
}

input3 = {
    'row_id': '5',
    'conditions.*.value' : ['1', '2', '3'],
    'conditions.*.var' : '',
    'conditions.*.type' : 'has_phrase',
    'conditions.*.name' : ['A','B',''],
}

input4 = {
    'row_id': '5',
    'conditions.1' : ['1', '', 'has_phrase', 'A'],
    'conditions.2' : ['2', '', 'has_phrase', 'B'],
    'conditions.3' : ['3', '', 'has_phrase', ''],
}

input5 = {
    'row_id': '5',
    'conditions.1' : ['1', '', 'has_phrase', 'A'],
    'conditions.2' : ['2', '', 'has_phrase', 'B'],
    'conditions.3' : ['3', '', 'has_phrase'],
}

input6 = {
    'row_id': '5',
    'conditions.1' : [['value', '1'], ['type', 'has_phrase'], ['name', 'A']],
    'conditions.2' : [['value', '2'], ['type', 'has_phrase'], ['name', 'B']],
    'conditions.3' : [['value', '3'], ['type', 'has_phrase']],
}

input7 = {
    'row_id': '5',
    'conditions.1' : ['1', '', 'has_phrase', ['name', 'A']],
    'conditions.2' : ['2', '', ['type', 'has_phrase'], ['name', 'B']],
    'conditions.3' : ['3', ['type', 'has_phrase']],
}

input8 = {
    'row_id': '5',
    'conditions' : [['1', '', 'has_phrase', 'A'], ['2', '', 'has_phrase', 'B'], ['3', '', 'has_phrase', '']],
}

input9 = {
    'row_id': '5',
    'conditions.1.value' : '1',
    'conditions.1.type' : 'has_phrase',
    'conditions.1.name' : 'A',
    'conditions.2.value' : '2',
    'conditions.2.type' : 'has_phrase',
    'conditions.2.name' : 'B',
    'conditions.3.value' : '3',
    'conditions.3.type' : 'has_phrase',
}


input_single_kwarg = {
    'row_id': '5',
    'conditions.1' : ['value', '3'],
}

output_single_kwarg_exp = FromWrong(**{
    'row_id': '5',
    'conditions': [
        {'value':'3', 'var':'', 'type':'', 'name':''},
    ]
})


class TestDifferentWays(unittest.TestCase):

    def setUp(self):
        self.parser = RowParser(FromWrong, MockCellParser())

    def test_different_ways(self):
        inputs = [input1, input2, input3, input4, input5, input6, input7, input8, input9]
        outputs = []

        for inp in inputs:
            out = self.parser.parse_row(inp)  # We get an instance of the model
            outputs.append(out)
            # Note: we can also serialize via out.json(indent=4) for printing
            # or out.dict()

        for out in outputs:
            self.assertEqual(out.dict(), output_instance)

    def test_single_kwarg(self):
        output_single_kwarg = self.parser.parse_row(input_single_kwarg)
        self.assertEqual(output_single_kwarg, output_single_kwarg_exp)


if __name__ == '__main__':
    unittest.main()
