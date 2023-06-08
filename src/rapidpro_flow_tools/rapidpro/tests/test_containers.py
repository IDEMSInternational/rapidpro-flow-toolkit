import unittest
import json

from rapidpro.models.containers import RapidProContainer, FlowContainer, UUIDDict
from rapidpro.models.actions import Group, SendMessageAction, AddContactGroupAction, RemoveContactGroupAction
from rapidpro.models.nodes import BasicNode, SwitchRouterNode, EnterFlowNode
from rapidpro.models.routers import SwitchRouter


def get_flow_with_group_and_flow_node():
    flow = FlowContainer('Group Flow')
    node = BasicNode()
    node.add_action(AddContactGroupAction([Group('No UUID Group'), Group('UUID Group', 'fake-uuid')]))
    flow.add_node(node)
    flow.add_node(EnterFlowNode('Second Flow'))
    return flow

def get_has_group_flow():
    flow = FlowContainer('Second Flow')
    node = SwitchRouterNode('@contact.groups')
    node.add_choice(
            comparison_variable='@contact.groups', 
            comparison_type='has_group', 
            comparison_arguments=[None, 'No UUID Group'], 
            category_name='No Category Name', 
            destination_uuid=None)
    node.add_choice(
            comparison_variable='@contact.groups', 
            comparison_type='has_group', 
            comparison_arguments=[None, 'UUID Group'], 
            category_name='Category Name', 
            destination_uuid=None)
    flow.add_node(node)
    flow.add_node(EnterFlowNode('Second Flow'))
    return flow

class TestActions(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_assign_group_and_flow(self):
        rpc = RapidProContainer()
        rpc.add_flow(get_flow_with_group_and_flow_node())
        self.assertIsNone(rpc.flows[0].nodes[0].actions[0].groups[0].uuid)
        self.assertEqual(rpc.flows[0].nodes[0].actions[0].groups[1].uuid, 'fake-uuid')
        self.assertIsNone(rpc.flows[0].nodes[1].actions[0].flow['uuid'])
        rpc.update_global_uuids()
        self.assertIsNotNone(rpc.flows[0].nodes[0].actions[0].groups[0].uuid)
        self.assertEqual(rpc.flows[0].nodes[0].actions[0].groups[1].uuid, 'fake-uuid')
        self.assertIsNotNone(rpc.flows[0].nodes[1].actions[0].flow['uuid'])

    def test_assign_group_predefined(self):
        rpc = RapidProContainer(groups=[Group('No UUID Group', 'ABCD')])
        rpc.add_flow(get_flow_with_group_and_flow_node())
        self.assertIsNone(rpc.flows[0].nodes[0].actions[0].groups[0].uuid)
        rpc.update_global_uuids()
        self.assertEqual(rpc.flows[0].nodes[0].actions[0].groups[0].uuid, 'ABCD')

    def test_assign_group_clash(self):
        rpc = RapidProContainer(groups=[Group('UUID Group', 'ABCD')])
        rpc.add_flow(get_flow_with_group_and_flow_node())
        self.assertEqual(rpc.flows[0].nodes[0].actions[0].groups[1].uuid, 'fake-uuid')
        with self.assertRaises(ValueError):
            # ValueError: Group/Flow UUID Group has multiple uuids: fake-uuid and ABCD
            rpc.update_global_uuids()

    def test_consistency(self):
        rpc = RapidProContainer()
        rpc.add_flow(get_flow_with_group_and_flow_node())
        rpc.add_flow(get_has_group_flow())
        rpc.update_global_uuids()
        self.assertEqual(rpc.flows[1].uuid, rpc.flows[0].nodes[1].actions[0].flow['uuid'])
        self.assertEqual(rpc.flows[1].nodes[0].router.cases[0].arguments[0], rpc.flows[0].nodes[0].actions[0].groups[0].uuid)
        self.assertEqual(rpc.flows[1].nodes[0].router.cases[1].arguments[0], 'fake-uuid')

