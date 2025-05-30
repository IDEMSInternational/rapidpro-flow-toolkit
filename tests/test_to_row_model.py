import unittest

from rpft.parsers.common.cellparser import CellParser
from rpft.parsers.common.rowdatasheet import RowDataSheet
from rpft.parsers.common.rowparser import RowParser
from rpft.parsers.creation.flowrowmodel import (
    Edge,
    FlowRowModel,
    Webhook,
    list_of_pairs_to_dict,
)
from rpft.rapidpro.models.actions import (
    AddContactGroupAction,
    Group,
    SendMessageAction,
    SetContactFieldAction,
    SetRunResultAction,
    WhatsAppMessageTemplating,
)
from rpft.rapidpro.models.common import mangle_string
from rpft.rapidpro.models.containers import FlowContainer
from rpft.rapidpro.models.nodes import (
    BasicNode,
    CallWebhookNode,
    EnterFlowNode,
    RandomRouterNode,
    SwitchRouterNode,
)
from tests.row_data import (
    get_message_with_templating,
    get_start_row,
    get_unconditional_node_from_1,
)


class TestMangle(unittest.TestCase):
    def test_mangle(self):
        mangled = mangle_string("ab@cd ef_gh-ij1234567")
        self.assertEqual(mangled, "abcd_ef_gh-ij12")


class TestToRowModels(unittest.TestCase):
    def compare_row_models_without_uuid(self, row_models1, row_models2):
        self.maxDiff = None
        self.assertEqual(len(row_models1), len(row_models2))
        for model1, model2 in zip(row_models1, row_models2):
            data1 = model1.model_dump()
            data2 = model2.model_dump()
            if not data1["node_uuid"] or not data2["node_uuid"]:
                # If one of them is blank, skip the comparison
                data1.pop("node_uuid")
                data2.pop("node_uuid")
            self.assertEqual(data1, data2)


class TestNodes(TestToRowModels):
    def test_basic_node(self):
        row_data = get_start_row()
        node = BasicNode()
        action = SendMessageAction(
            row_data.mainarg_message_text, quick_replies=row_data.choices
        )
        node.add_action(action)
        node.initiate_row_models(1, Edge(from_="start"))
        row_models = node.get_row_models()
        self.compare_row_models_without_uuid(row_models, [row_data])

    def test_templating_node(self):
        row_data = get_message_with_templating()
        templating = WhatsAppMessageTemplating.from_whats_app_templating_model(
            row_data.wa_template
        )
        node = BasicNode()
        action = SendMessageAction(
            row_data.mainarg_message_text,
            quick_replies=row_data.choices,
            templating=templating,
        )
        node.add_action(action)
        node.initiate_row_models(1, Edge(from_="start"))
        row_models = node.get_row_models()
        self.compare_row_models_without_uuid(row_models, [row_data])

    def test_basic_node_two_actions(self):
        row_data1 = get_start_row()
        row_data2 = get_unconditional_node_from_1()
        node = BasicNode()
        action = SendMessageAction(
            row_data1.mainarg_message_text, quick_replies=row_data1.choices
        )
        node.add_action(action)
        action = SendMessageAction(
            row_data2.mainarg_message_text, quick_replies=row_data2.choices
        )
        node.add_action(action)
        node.initiate_row_models("1", Edge(from_="start"))
        row_models = node.get_row_models()
        # The section action gets row ID 1.1, which needs to be remapped to 2.
        # When converting flows to rows, this remapping is done automatically.
        row_models[1].row_id = "2"
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_add_group_node(self):
        row_data = FlowRowModel(
            **{
                "row_id": "1",
                "type": "add_to_group",
                "mainarg_groups": ["test group"],
                "obj_id": "8224bfe2-acec-434f-bc7c-14c584fc4bc8",
                "edges": [{"from_": "start"}],
                "ui_position": ["123", "456"],
                "node_uuid": "224f6caa-fd25-47d3-96a9-3d43506b7878",
            }
        )
        node = BasicNode(
            uuid=row_data.node_uuid, ui_pos=(int(p) for p in row_data.ui_position)
        )
        action = AddContactGroupAction(
            [Group(row_data.mainarg_groups[0], row_data.obj_id)]
        )
        node.add_action(action)
        node.initiate_row_models(1, Edge(from_="start"))
        row_models = node.get_row_models()
        self.compare_row_models_without_uuid(row_models, [row_data])


class TestFlowContainer(TestToRowModels):
    def test_basic_node(self):
        row_data = get_start_row()
        node = BasicNode()
        action = SendMessageAction(
            row_data.mainarg_message_text, quick_replies=row_data.choices
        )
        node.add_action(action)
        container = FlowContainer("test_flow")
        container.add_node(node)
        row_models = container.to_rows(numbered=True)
        self.compare_row_models_without_uuid(row_models, [row_data])

    def test_webhook_node(self):
        webhook_data = {
            "url": "the_url",
            "method": "POST",
            "body": "payload",
        }
        headers = [["header1", "value1"], ["header2", "value2"]]
        headers_dict = list_of_pairs_to_dict(headers)
        row_data = FlowRowModel(
            row_id="webhook.the_url",
            edges=[{"from_": "start"}],
            type="call_webhook",
            webhook=Webhook(headers=headers, **webhook_data),
            save_name="result name",
        )
        node = CallWebhookNode(
            result_name="result name", headers=headers_dict, **webhook_data
        )

        container = FlowContainer("test_flow")
        container.add_node(node)
        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data])

    def test_two_basic_nodes(self):
        row_data1 = get_start_row()
        row_data2 = get_unconditional_node_from_1()
        node1 = BasicNode()
        node2 = BasicNode()
        action1 = SendMessageAction(
            row_data1.mainarg_message_text, quick_replies=row_data1.choices
        )
        action2 = SendMessageAction(
            row_data2.mainarg_message_text, quick_replies=row_data2.choices
        )
        node1.add_action(action1)
        node2.add_action(action2)
        node1.update_default_exit(node2.uuid)
        container = FlowContainer("test_flow")
        container.add_node(node1)
        container.add_node(node2)
        row_models = container.to_rows(numbered=True)
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_conditional_edge(self):
        row_data1 = FlowRowModel(
            **{
                "row_id": "switch.fields_name",
                "type": "split_by_value",
                "edges": [{"from_": "start"}],
                "mainarg_expression": "@fields.name",
            }
        )
        row_data2 = FlowRowModel(
            **{
                "row_id": "msg.Message_if_fiel",
                "type": "send_message",
                "edges": [
                    {
                        "from_": "switch.fields_name",
                        "condition": {
                            "value": "3",
                            "variable": "@fields.name",
                            "type": "has_phrase",
                            "name": "3",
                        },
                    }
                ],
                "mainarg_message_text": "Message if @fields.name == 3",
            }
        )
        case = row_data2.edges[0].condition
        container = FlowContainer("test_flow")

        node1 = SwitchRouterNode(case.variable)
        node2 = BasicNode()

        node1.add_choice(case.variable, case.type, [case.value], case.name, node2.uuid)
        container.add_node(node1)

        action2 = SendMessageAction(
            row_data2.mainarg_message_text, quick_replies=row_data2.choices
        )
        node2.add_action(action2)
        container.add_node(node2)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_conditional_edge2(self):
        row_data1 = FlowRowModel(
            **{
                "row_id": "switch.contact_groups",
                "type": "split_by_group",
                "edges": [{"from_": "start"}],
                "mainarg_groups": ["my group"],
                "obj_id": "12345678",
            }
        )
        row_data2 = FlowRowModel(
            **{
                "row_id": "set_contact_field.my_variable",
                "type": "save_value",
                "edges": [
                    {
                        "from_": "switch.contact_groups",
                        "condition": {"value": "my group"},
                    }
                ],
                "mainarg_value": "my value",
                "save_name": "my_variable",
            }
        )
        case = row_data2.edges[0].condition
        container = FlowContainer("test_flow")

        node1 = SwitchRouterNode("@contact.groups")
        node2 = BasicNode()

        # The arguments for this choice is [group uuid, group name]
        node1.add_choice(
            case.variable,
            case.type or "has_group",
            [row_data1.obj_id, case.value],
            case.name,
            node2.uuid,
        )
        container.add_node(node1)

        action2 = SetContactFieldAction(row_data2.save_name, row_data2.mainarg_value)
        node2.add_action(action2)
        container.add_node(node2)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_random_double_edge(self):
        # Two edges into the same node (i.e. forward edge in the tree)
        # Uses random router

        row_data1 = FlowRowModel(
            **{
                "row_id": "random",
                "type": "split_random",
                "edges": [{"from_": "start"}],
            }
        )

        row_data2 = FlowRowModel(
            **{
                "row_id": "msg.Second_node_mes",
                "type": "send_message",
                "edges": [
                    {
                        "from_": "random",
                        "condition": {"value": "1"},
                    },
                    {
                        "from_": "random",
                        "condition": {"value": "2"},
                    },
                ],
                "mainarg_message_text": "Second node message",
            }
        )

        container = FlowContainer("test_flow")

        node1 = RandomRouterNode()
        node2 = BasicNode()

        node1.add_choice(row_data2.edges[0].condition.value, node2.uuid)
        node1.add_choice(row_data2.edges[1].condition.value, node2.uuid)
        container.add_node(node1)

        action2 = SendMessageAction(row_data2.mainarg_message_text)
        node2.add_action(action2)
        container.add_node(node2)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])

    def test_cyclic_wait_edge(self):
        # An edge for a wait_for_response node to itself (cycle) via go_to

        row_data1 = FlowRowModel(
            **{
                "row_id": "wait_for.wait_result",
                "type": "wait_for_response",
                "save_name": "wait_result",
                "no_response": "300",
                "edges": [{"from_": "start"}],
            }
        )
        # A proper case
        row_data2 = FlowRowModel(
            **{
                "row_id": "goto.wait_for.wait_result",
                "type": "go_to",
                "edges": [
                    {
                        "from_": "wait_for.wait_result",
                        "condition": {
                            "value": "word",
                            "variable": "@input.text",
                            "type": "has_any_word",
                            "name": "Word",
                        },
                    }
                ],
                "mainarg_destination_row_ids": ["wait_for.wait_result"],
            }
        )
        # The 'Other' category
        row_data3 = FlowRowModel(
            **{
                "row_id": "msg.Node_message_te",
                "type": "send_message",
                "edges": [
                    {
                        "from_": "wait_for.wait_result",
                    }
                ],
                "mainarg_message_text": "Node message text number 2",
            }
        )
        # The no response category
        row_data4 = FlowRowModel(
            **{
                "row_id": "msg.Node_message_te.1",
                "type": "send_message",
                "edges": [
                    {
                        "from_": "wait_for.wait_result",
                        "condition": {"value": "No Response"},
                    }
                ],
                "mainarg_message_text": "Node message text number 3",
            }
        )

        case1 = row_data2.edges[0].condition
        container = FlowContainer("test_flow")
        node1 = SwitchRouterNode(
            "@input.text",
            result_name=row_data1.save_name,
            wait_timeout=int(row_data1.no_response),
        )
        node2 = BasicNode()
        node3 = BasicNode()
        node1.add_choice(
            case1.variable, case1.type, [case1.value], case1.name, node1.uuid
        )
        node1.update_default_exit(node2.uuid)
        node1.update_no_response_exit(node3.uuid)
        container.add_node(node1)

        action2 = SendMessageAction(row_data3.mainarg_message_text)
        node2.add_action(action2)
        container.add_node(node2)
        action3 = SendMessageAction(row_data4.mainarg_message_text)
        node3.add_action(action3)
        container.add_node(node3)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(
            row_models, [row_data1, row_data2, row_data3, row_data4]
        )

    def test_enter_flow_edge(self):
        # Test expired (default) edge of enter_flow node
        # test save_flow_result with a @result (set_run_result in rapidpro)

        row_data1 = FlowRowModel(
            **{
                "row_id": "flow.sample_flow",
                "type": "start_new_flow",
                "mainarg_flow_name": "sample_flow",
                "obj_id": "8224bfe2-acec-434f-bc7c-14c584fc4bc8",
                "edges": [{"from_": "start"}],
            }
        )

        row_data2 = FlowRowModel(
            **{
                "row_id": "set_run_result.my_result",
                "type": "save_flow_result",
                "edges": [
                    {
                        "from_": "flow.sample_flow",
                        "condition": {"value": "expired"},
                    }
                ],
                "mainarg_value": "Value",
                "save_name": "my result",
            }
        )

        case1 = row_data2.edges[0].condition
        container = FlowContainer("test_flow")

        node1 = EnterFlowNode(row_data1.mainarg_flow_name, row_data1.obj_id)
        node2 = BasicNode()
        node1.add_choice(
            case1.variable,
            case1.type or "has_only_text",
            [case1.value],
            case1.name,
            node2.uuid,
            is_default=True,
        )
        container.add_node(node1)

        action2 = SetRunResultAction(row_data2.save_name, row_data2.mainarg_value)
        node2.add_action(action2)
        container.add_node(node2)

        row_models = container.to_rows()
        self.compare_row_models_without_uuid(row_models, [row_data1, row_data2])


class TestRowModelExport(unittest.TestCase):
    def test_row_model_export(self):
        row_data = FlowRowModel(
            **{
                "row_id": "1",
                "type": "send_message",
                "mainarg_message_text": "Hello",
                "choices": ["QR1", "QR2", "QR3"],
                "edges": [{"from_": "start"}],
                "node_uuid": "224f6caa-fd25-47d3-96a9-3d43506b7878",
                "ui_position": ["123", "456"],
            }
        )

        # Because default values are '', even blank fields are exported.
        # This may change in the future.
        expected_headers = [
            "row_id",
            "type",
            "edges.1.from",
            "message_text",
            "choices.1",
            "choices.2",
            "choices.3",
            "_nodeId",
            "_ui_position",
        ]
        expected_content = (
            "1",
            "send_message",
            "start",
            "Hello",
            "QR1",
            "QR2",
            "QR3",
            "224f6caa-fd25-47d3-96a9-3d43506b7878",
            "123|456",
        )

        sheet = RowDataSheet(RowParser(FlowRowModel, CellParser()), [row_data])
        tablib_sheet = sheet.convert_to_tablib()
        self.assertEqual(tablib_sheet.headers, expected_headers)
        self.assertEqual(tablib_sheet[0], expected_content)
