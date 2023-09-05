import unittest
import json

from rpft.rapidpro.models.actions import Action, Group
from rpft.rapidpro.models.common import Exit
from rpft.rapidpro.models.routers import RouterCase, RouterCategory, BaseRouter
from rpft.rapidpro.models.nodes import BaseNode
from rpft.rapidpro.models.containers import FlowContainer, RapidProContainer
from rpft.rapidpro.models.campaigns import Campaign, CampaignEvent
from tests import TESTS_ROOT


class TestImportExport(unittest.TestCase):
    def setUp(self) -> None:
        self.data_dir = TESTS_ROOT / "data"

    def test_all_action_types(self):
        actionFilenamesList = self.data_dir.glob('actions/*.json')
        for filename in actionFilenamesList:
            with open(filename, 'r') as f:
                action_data = json.load(f)
            action = Action.from_dict(action_data)
            render_output = action.render()
            self.assertEqual(render_output, action_data, msg=filename)

    def test_exits(self):
        with open(self.data_dir / 'exits/exit.json', 'r') as f:
            data = json.load(f)
        exit = Exit.from_dict(data)
        render_output = exit.render()
        self.assertEqual(render_output, data)

    def test_groups(self):
        with open(self.data_dir / 'groups/group.json', 'r') as f:
            data = json.load(f)
        group = Group.from_dict(data)
        render_output = group.render()
        self.assertEqual(render_output, data)

    def test_cases(self):
        with open(self.data_dir / 'routers/case.json', 'r') as f:
            data = json.load(f)
        case = RouterCase.from_dict(data)
        render_output = case.render()
        self.assertEqual(render_output, data)

    def test_categories(self):
        with open(self.data_dir / 'routers/category.json', 'r') as f:
            data = json.load(f)
        with open(self.data_dir / 'routers/exits.json', 'r') as f:
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
        routerFilenamesList = self.data_dir.glob('routers/router_*.json')
        for filename in routerFilenamesList:
            with open(filename, 'r') as f:
                router_data = json.load(f)
            with open(self.data_dir / 'routers/exits.json', 'r') as f:
                exit_data = json.load(f)
            exits = [Exit.from_dict(exit) for exit in exit_data]
            router = BaseRouter.from_dict(router_data, exits)
            render_output = router.render()
            self.assertEqual(render_output, router_data, msg=filename)

    def test_all_node_types(self):
        self.maxDiff = None
        nodeFilenamesList = self.data_dir.glob('nodes/node_*.json')
        for filename in nodeFilenamesList:
            with open(filename, 'r') as f:
                node_data = json.load(f)
            node = BaseNode.from_dict(node_data)
            render_output = node.render()
            self.assertEqual(render_output, node_data, msg=filename)

    def test_flow_containers(self):
        self.maxDiff = None
        # TODO: Add test with localization (of different objects) to ensure it is maintained
        containerFilenamesList = self.data_dir.glob('containers/flow_container_*.json')
        for filename in containerFilenamesList:
            with open(filename, 'r') as f:
                container_data = json.load(f)
            container = FlowContainer.from_dict(container_data)
            render_output = container.render()
            # TODO: compare nodes/UI element-wise, for smaller error output?
            self.assertEqual(render_output, container_data, msg=filename)

    def test_rapidpro_containers(self):
        self.maxDiff = None
        containerFilenamesList = self.data_dir.glob('containers/rapidpro_container_*.json')
        for filename in containerFilenamesList:
            with open(filename, 'r') as f:
                container_data = json.load(f)
            container = RapidProContainer.from_dict(container_data)
            render_output = container.render()
            self.assertEqual(render_output, container_data, msg=filename)

    def test_campaign_events(self):
        self.maxDiff = None
        filenamesList = self.data_dir.glob('campaigns/event_*.json')
        for filename in filenamesList:
            with open(filename, 'r') as f:
                data = json.load(f)
            event = CampaignEvent.from_dict(data)
            render_output = event.render()
            self.assertEqual(render_output, data, msg=filename)

    def test_campaigns(self):
        self.maxDiff = None
        filenamesList = self.data_dir.glob('campaigns/campaign_*.json')
        for filename in filenamesList:
            with open(filename, 'r') as f:
                data = json.load(f)
            campaign = Campaign.from_dict(data)
            render_output = campaign.render()
            self.assertEqual(render_output, data, msg=filename)
