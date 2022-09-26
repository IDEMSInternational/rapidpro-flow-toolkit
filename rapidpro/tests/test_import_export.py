import unittest
import json
import glob

from rapidpro.models.actions import Action, Group
from rapidpro.models.common import Exit
from rapidpro.models.routers import RouterCase, RouterCategory, BaseRouter
from rapidpro.models.nodes import BaseNode


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

    def test_cases(self):
        with open('rapidpro/tests/data/routers/case.json', 'r') as f:
           data = json.load(f)
        case = RouterCase.from_dict(data)
        render_output = case.render()
        self.assertEqual(render_output, data)

    def test_categories(self):
        with open('rapidpro/tests/data/routers/category.json', 'r') as f:
           data = json.load(f)
        with open('rapidpro/tests/data/routers/exits.json', 'r') as f:
           exit_data = json.load(f)
        exits = [Exit.from_dict(exit) for exit in exit_data]
        category = RouterCategory.from_dict(data, exits)
        render_output = category.render()
        self.assertEqual(render_output, data)

    def test_all_router_types(self):
        # Note: These test cases assume that the default category
        # within switch routers is always the last one.
        # This might change once we support "Expired" categories
        self.maxDiff = None
        routerFilenamesList = glob.glob('rapidpro/tests/data/routers/router_*.json')
        for filename in routerFilenamesList:
            with open(filename, 'r') as f:
               router_data = json.load(f)
            with open('rapidpro/tests/data/routers/exits.json', 'r') as f:
               exit_data = json.load(f)
            exits = [Exit.from_dict(exit) for exit in exit_data]
            router = BaseRouter.from_dict(router_data, exits)
            render_output = router.render()
            self.assertEqual(render_output, router_data)

    def test_all_node_types(self):
        # Note: These test cases assume that the default category
        # within switch routers is always the last one.
        # This might change once we support "Expired" categories
        self.maxDiff = None
        nodeFilenamesList = glob.glob('rapidpro/tests/data/nodes/node_*.json')
        for filename in nodeFilenamesList:
            with open(filename, 'r') as f:
               node_data = json.load(f)
            node = BaseNode.from_dict(node_data)
            render_output = node.render()
            self.assertEqual(render_output, node_data)
