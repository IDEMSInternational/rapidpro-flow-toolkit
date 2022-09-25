import unittest
import json
import glob

from rapidpro.models.actions import Action, Group
from rapidpro.models.common import Exit


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
            self.assertEqual(render_output, action_data)

    def test_exits(self):
        with open('rapidpro/tests/data/exits/exit.json', 'r') as f:
           data = json.load(f)
        exit = Exit.from_dict(data)
        render_output = exit.render()
        self.assertEqual(render_output, data)

    def test_groups(self):
        with open('rapidpro/tests/data/groups/group.json', 'r') as f:
           data = json.load(f)
        group = Group.from_dict(data)
        render_output = group.render()
        self.assertEqual(render_output, data)
