import unittest

from rpft.rapidpro.models.containers import RapidProContainer, FlowContainer
from rpft.rapidpro.models.actions import Group, AddContactGroupAction
from rpft.rapidpro.models.nodes import BasicNode, SwitchRouterNode, EnterFlowNode
from rpft.rapidpro.models.campaigns import Campaign, CampaignEvent
from rpft.rapidpro.models.triggers import Trigger


def get_flow_with_group_and_flow_node():
    flow = FlowContainer("Group Flow")
    node = BasicNode()
    node.add_action(
        AddContactGroupAction(
            [Group("No UUID Group"), Group("UUID Group", "fake-uuid")]
        )
    )
    flow.add_node(node)
    flow.add_node(EnterFlowNode("Second Flow"))
    return flow


def get_has_group_flow():
    flow = FlowContainer("Second Flow")
    node = SwitchRouterNode("@contact.groups")
    node.add_choice(
        comparison_variable="@contact.groups",
        comparison_type="has_group",
        comparison_arguments=[None, "No UUID Group"],
        category_name="No Category Name",
        destination_uuid=None,
    )
    node.add_choice(
        comparison_variable="@contact.groups",
        comparison_type="has_group",
        comparison_arguments=[None, "UUID Group"],
        category_name="Category Name",
        destination_uuid=None,
    )
    flow.add_node(node)
    flow.add_node(EnterFlowNode("Second Flow"))
    return flow


class TestRapidProContainer(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_assign_group_and_flow(self):
        rpc = RapidProContainer()
        rpc.add_flow(get_flow_with_group_and_flow_node())
        self.assertIsNone(rpc.flows[0].nodes[0].actions[0].groups[0].uuid)
        self.assertEqual(rpc.flows[0].nodes[0].actions[0].groups[1].uuid, "fake-uuid")
        self.assertIsNone(rpc.flows[0].nodes[1].actions[0].flow.uuid)
        rpc.update_global_uuids()
        self.assertIsNotNone(rpc.flows[0].nodes[0].actions[0].groups[0].uuid)
        self.assertEqual(rpc.flows[0].nodes[0].actions[0].groups[1].uuid, "fake-uuid")
        self.assertIsNotNone(rpc.flows[0].nodes[1].actions[0].flow.uuid)

    def test_assign_group_predefined(self):
        rpc = RapidProContainer(groups=[Group("No UUID Group", "ABCD")])
        rpc.add_flow(get_flow_with_group_and_flow_node())
        self.assertIsNone(rpc.flows[0].nodes[0].actions[0].groups[0].uuid)
        rpc.update_global_uuids()
        self.assertEqual(rpc.flows[0].nodes[0].actions[0].groups[0].uuid, "ABCD")

    def test_assign_group_clash(self):
        rpc = RapidProContainer(groups=[Group("UUID Group", "ABCD")])
        rpc.add_flow(get_flow_with_group_and_flow_node())
        self.assertEqual(rpc.flows[0].nodes[0].actions[0].groups[1].uuid, "fake-uuid")
        with self.assertRaises(ValueError):
            # ValueError: Group/Flow UUID Group has multiple uuids: fake-uuid and ABCD
            rpc.update_global_uuids()

    def test_consistency(self):
        rpc = RapidProContainer()
        rpc.add_flow(get_flow_with_group_and_flow_node())
        rpc.add_flow(get_has_group_flow())
        rpc.update_global_uuids()
        self.assertEqual(rpc.flows[1].uuid, rpc.flows[0].nodes[1].actions[0].flow.uuid)
        self.assertEqual(
            rpc.flows[1].nodes[0].router.cases[0].arguments[0],
            rpc.flows[0].nodes[0].actions[0].groups[0].uuid,
        )
        self.assertEqual(
            rpc.flows[1].nodes[0].router.cases[1].arguments[0], "fake-uuid"
        )

    def test_assign_uuids_to_campaign(self):
        rpc = RapidProContainer()
        rpc.add_flow(get_flow_with_group_and_flow_node())
        event = CampaignEvent(
            offset=1234,
            unit="H",
            event_type="F",
            delivery_hour=-1,
            start_mode="I",
            relative_to_label="Created On",
            flow_name="Second Flow",
        )
        campaign = Campaign("My Campaign", Group("UUID Group"), events=[event])
        rpc.add_campaign(campaign)
        rpc.update_global_uuids()
        self.assertEqual(rpc.campaigns[0].group.uuid, "fake-uuid")
        self.assertEqual(
            rpc.campaigns[0].events[0].flow.uuid,
            rpc.flows[0].nodes[1].actions[0].flow.uuid,
        )

    def test_get_uuids_from_campaign(self):
        rpc = RapidProContainer()
        rpc.add_flow(get_flow_with_group_and_flow_node())
        event = CampaignEvent(
            offset=1234,
            unit="H",
            event_type="F",
            delivery_hour=-1,
            start_mode="I",
            relative_to_label="Created On",
            flow_name="Second Flow",
            flow_uuid="fake-flow-uuid",
        )
        campaign = Campaign(
            "My Campaign", Group("No UUID Group", "fake-group-uuid"), events=[event]
        )
        rpc.add_campaign(campaign)
        rpc.update_global_uuids()
        self.assertEqual(rpc.campaigns[0].group.uuid, "fake-group-uuid")
        self.assertEqual(
            rpc.flows[0].nodes[0].actions[0].groups[0].uuid, "fake-group-uuid"
        )
        self.assertEqual(rpc.flows[0].nodes[1].actions[0].flow.uuid, "fake-flow-uuid")
        self.assertEqual(rpc.campaigns[0].events[0].flow.uuid, "fake-flow-uuid")

    def test_get_uuids_from_trigger(self):
        rpc = RapidProContainer()
        rpc.add_flow(get_flow_with_group_and_flow_node())
        trigger = Trigger(
            "K",
            "keyword",
            flow_name="Second Flow",
            flow_uuid="fake-flow-uuid",
            group_names=["No UUID Group"],
            group_uuids=["fake-group-uuid"],
        )
        rpc.add_trigger(trigger)
        rpc.update_global_uuids()
        self.assertEqual(rpc.triggers[0].groups[0].uuid, "fake-group-uuid")
        self.assertEqual(
            rpc.flows[0].nodes[0].actions[0].groups[0].uuid, "fake-group-uuid"
        )
        self.assertEqual(rpc.flows[0].nodes[1].actions[0].flow.uuid, "fake-flow-uuid")
        self.assertEqual(rpc.triggers[0].flow.uuid, "fake-flow-uuid")
