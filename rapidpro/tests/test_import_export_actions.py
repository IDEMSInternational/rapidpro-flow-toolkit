import unittest
import json
import glob

from rapidpro.models.actions import Action


class TestActions(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_all_action_types(self):
        actionFilenamesList = glob.glob('rapidpro/tests/data/actions/*.json')
        for filename in actionFilenamesList:
            with open(filename, 'r') as f:
               action_data = json.load(f)
            action = Action.from_dict(action_data)
            render_output = action.render()
            # print(type(action), render_output, action_data)
            self.assertEqual(render_output, action_data)
