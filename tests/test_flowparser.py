import copy
import json
import tablib
from unittest import TestCase

from rpft.parsers.common.cellparser import CellParser
from rpft.parsers.common.rowparser import RowParser
from rpft.parsers.creation.flowrowmodel import FlowRowModel
from rpft.parsers.creation.flowparser import FlowParser
from rpft.rapidpro.models.actions import Group, AddContactGroupAction
from rpft.rapidpro.models.containers import RapidProContainer, FlowContainer
from rpft.rapidpro.models.nodes import BasicNode
from rpft.rapidpro.simulation import (
    Context,
    find_destination_uuid,
    find_node_by_uuid,
    traverse_flow,
)

from tests import TESTS_ROOT
from tests.mocks import MockSheetParser
from tests.row_data import (
    get_conditional_node_from_1,
    get_message_with_templating,
    get_unconditional_node_from_1,
    get_start_row,
)
from tests.utils import get_dict_from_csv, get_table_from_file


class TestParsing(TestCase):
    def setUp(self) -> None:
        self.row_parser = RowParser(FlowRowModel, CellParser())

    def get_render_output_from_file(self, flow_name, filename):
        self.rows = [
            self.row_parser.parse_row(row) for row in get_dict_from_csv(filename)
        ]
        return self.get_render_output(flow_name, self.rows)

    def get_render_output(self, flow_name, input_rows):
        return (
            FlowParser(
                RapidProContainer(),
                flow_name=flow_name,
                sheet_parser=MockSheetParser(input_rows),
            )
            .parse()
            .render()
        )

    def test_send_message(self):
        output = self.get_render_output("send_message", [get_start_row()])

        action = output["nodes"][0]["actions"][0]
        self.assertEqual(action["type"], "send_msg")
        self.assertEqual(action["text"], "Text of message")
        self.assertEqual(len(action["attachments"]), 0)
        self.assertEqual(action["quick_replies"], ["Answer 1", "Answer 2"])

    def test_send_message_with_template(self):
        output = self.get_render_output(
            "send_message_with_template",
            [get_start_row(), get_message_with_templating()],
        )

        self.assertNotIn("templating", output["nodes"][0]["actions"][0])

        action = output["nodes"][1]["actions"][0]
        self.assertIn("uuid", action["templating"])
        self.assertEqual(action["templating"]["template"]["name"], "template name")
        self.assertEqual(action["templating"]["template"]["uuid"], "template uuid")
        self.assertEqual(action["templating"]["variables"], ["var1", "var2"])

    def test_linear(self):
        row = get_unconditional_node_from_1()
        row.edges[0].from_ = ""  # implicit continue from last node

        output = self.get_render_output("linear", [get_start_row(), row])

        node_0, node_1 = output["nodes"]
        self.assertEqual(node_1["actions"][0]["text"], "Unconditional message")
        self.assertEqual(len(node_0["exits"]), 1)
        self.assertIsNone(node_0.get("router"))
        self.assertEqual(node_0["exits"][0]["destination_uuid"], node_1["uuid"])
        self.assertEqual(node_1["exits"][0]["destination_uuid"], None)

    def test_only_conditional(self):
        output = self.get_render_output(
            "only_conditional",
            [get_start_row(), get_conditional_node_from_1()],
        )

        self.assertEqual(len(output["nodes"]), 3)
        node_0, node_1, node_2 = output["nodes"]
        self.assertEqual(node_2["actions"][0]["text"], "Message if @fields.name == 3")
        self.assertEqual(len(node_1["exits"]), 2)
        self.assertIsNone(node_0.get("router"))
        self.assertIsNotNone(node_1.get("router"))
        self.assertEqual(node_0["exits"][0]["destination_uuid"], node_1["uuid"])
        self.assertEqual(node_1["exits"][0]["destination_uuid"], node_2["uuid"])
        self.assertEqual(node_1["exits"][1]["destination_uuid"], None)
        self.assertEqual(node_2["exits"][0]["destination_uuid"], None)

    def test_split1(self):
        output = self.get_render_output(
            "split",
            [
                get_start_row(),
                get_unconditional_node_from_1(),
                get_conditional_node_from_1(),
            ],
        )

        self.assert_split(output)

    def test_split2(self):
        output = self.get_render_output(
            "split",
            [
                get_start_row(),
                get_conditional_node_from_1(),
                get_unconditional_node_from_1(),
            ],
        )

        self.assert_split(output)

    def assert_split(self, output):
        node_start = output["nodes"][0]
        node_switch = find_node_by_uuid(
            output, node_start["exits"][0]["destination_uuid"]
        )
        default_destination = find_destination_uuid(
            node_switch, Context(variables={"@fields.name": "5"})
        )
        node_2 = find_node_by_uuid(output, default_destination)
        cond_destination = find_destination_uuid(
            node_switch, Context(variables={"@fields.name": "3"})
        )
        node_3 = find_node_by_uuid(output, cond_destination)

        self.assertEqual(node_3["actions"][0]["text"], "Message if @fields.name == 3")
        self.assertEqual(node_2["actions"][0]["text"], "Unconditional message")
        self.assertEqual(len(node_switch["exits"]), 2)
        self.assertIsNone(node_start.get("router"))
        self.assertIsNotNone(node_switch.get("router"))

    def test_no_switch_node_rows(self):
        output = self.get_render_output_from_file(
            "no_switch_node", "input/no_switch_nodes.csv"
        )

        # Check that node UUIDs are maintained
        nodes = output["nodes"]
        all_node_uuids = [row.node_uuid for row in self.rows]
        # Rows 0,1,2,3 and rows -3,-2 are actions joined into a single node.
        expected_node_uuids = all_node_uuids[3:-3] + all_node_uuids[-2:]
        self.assertEqual(
            expected_node_uuids,
            [node["uuid"] for node in nodes],
        )

        self.assertEqual(output["name"], "no_switch_node")
        self.assertEqual(output["type"], "messaging")
        self.assertEqual(output["language"], "eng")

        self.assertEqual(len(nodes), 8)

        node_0 = nodes[0]
        self.assertEqual(len(node_0["actions"]), 4)
        self.assertEqual(node_0["actions"][0]["type"], "send_msg")
        self.assertEqual(node_0["actions"][0]["text"], "this is a send message node")
        self.assertEqual(len(node_0["actions"][0]["attachments"]), 0)
        self.assertIn("qr1", node_0["actions"][0]["quick_replies"])
        self.assertIn("qr2", node_0["actions"][0]["quick_replies"])

        self.assertEqual(node_0["actions"][1]["type"], "send_msg")
        self.assertEqual(node_0["actions"][1]["text"], "message with image")
        self.assertEqual(len(node_0["actions"][1]["attachments"]), 1)
        self.assertEqual(node_0["actions"][1]["attachments"][0], "image:image u")
        self.assertEqual(len(node_0["actions"][1]["quick_replies"]), 0)

        self.assertEqual(node_0["actions"][2]["type"], "send_msg")
        self.assertEqual(node_0["actions"][2]["text"], "message with audio")
        self.assertEqual(len(node_0["actions"][2]["attachments"]), 1)
        self.assertEqual(node_0["actions"][2]["attachments"][0], "audio:audio u")
        self.assertEqual(len(node_0["actions"][2]["quick_replies"]), 0)

        self.assertEqual(node_0["actions"][3]["type"], "send_msg")
        self.assertEqual(node_0["actions"][3]["text"], "message with video")
        self.assertEqual(len(node_0["actions"][3]["attachments"]), 1)
        self.assertEqual(node_0["actions"][3]["attachments"][0], "video:video u")
        self.assertEqual(len(node_0["actions"][3]["quick_replies"]), 0)

        node_1 = nodes[1]
        self.assertEqual(node_0["exits"][0]["destination_uuid"], node_1["uuid"])
        self.assertEqual(len(node_1["actions"]), 1)
        self.assertEqual(node_1["actions"][0]["type"], "set_contact_field")
        self.assertEqual(node_1["actions"][0]["field"]["key"], "test_variable")
        self.assertEqual(node_1["actions"][0]["field"]["name"], "test variable")
        self.assertEqual(node_1["actions"][0]["value"], "test value")

        node_2 = nodes[2]
        self.assertEqual(node_1["exits"][0]["destination_uuid"], node_2["uuid"])
        self.assertEqual(len(node_2["actions"]), 1)
        self.assertEqual(node_2["actions"][0]["type"], "add_contact_groups")
        self.assertEqual(len(node_2["actions"][0]["groups"]), 1)
        self.assertEqual(node_2["actions"][0]["groups"][0]["name"], "test group")

        node_3 = nodes[3]
        self.assertEqual(node_2["exits"][0]["destination_uuid"], node_3["uuid"])
        self.assertEqual(len(node_3["actions"]), 1)
        self.assertEqual("remove_contact_groups", node_3["actions"][0]["type"])
        self.assertEqual(len(node_3["actions"][0]["groups"]), 1)
        self.assertEqual("test group", node_3["actions"][0]["groups"][0]["name"])

        # Make sure it's the same group
        self.assertEqual(
            node_2["actions"][0]["groups"][0]["uuid"],
            node_3["actions"][0]["groups"][0]["uuid"],
        )

        node_4 = nodes[4]
        self.assertEqual(node_3["exits"][0]["destination_uuid"], node_4["uuid"])
        self.assertEqual(len(node_4["actions"]), 1)
        self.assertEqual("set_run_result", node_4["actions"][0]["type"])
        self.assertEqual("result name", node_4["actions"][0]["name"])
        self.assertEqual("result value", node_4["actions"][0]["value"])
        self.assertEqual("my_result_cat", node_4["actions"][0]["category"])

        node_5 = nodes[5]
        self.assertEqual(node_4["exits"][0]["destination_uuid"], node_5["uuid"])
        self.assertEqual(len(node_5["actions"]), 2)
        self.assertEqual(node_5["actions"][0]["type"], "set_contact_language")
        self.assertEqual(node_5["actions"][0]["language"], "eng")
        self.assertEqual(node_5["actions"][1]["type"], "set_contact_name")
        self.assertEqual(node_5["actions"][1]["name"], "John Doe")

        node_6 = nodes[6]
        self.assertEqual(node_5["exits"][0]["destination_uuid"], node_6["uuid"])

        node_7 = nodes[7]
        self.assertEqual(len(node_7["actions"]), 1)
        self.assertEqual("remove_contact_groups", node_7["actions"][0]["type"])
        self.assertEqual(len(node_7["actions"][0]["groups"]), 0)
        self.assertTrue(node_7["actions"][0]["all_groups"])
        self.assertIsNone(node_7["exits"][0]["destination_uuid"])

        # Check UI positions/types of the first two nodes
        render_ui = output["_ui"]["nodes"]
        self.assertIn(node_0["uuid"], render_ui)
        pos0 = render_ui[node_0["uuid"]]["position"]
        self.assertEqual((280, 73), (pos0["left"], pos0["top"]))
        self.assertEqual("execute_actions", render_ui[node_0["uuid"]]["type"])
        self.assertIn(node_1["uuid"], render_ui)
        pos1 = render_ui[node_1["uuid"]]["position"]
        self.assertEqual((280, 600), (pos1["left"], pos1["top"]))
        self.assertEqual("execute_actions", render_ui[node_1["uuid"]]["type"])

    def test_switch_node_rows(self):
        output = self.get_render_output_from_file(
            "switch_node", "input/switch_nodes.csv"
        )

        # Check that node UUIDs are maintained
        nodes = output["nodes"]
        self.assertEqual(
            [row.node_uuid for row in self.rows],
            [node["uuid"] for node in nodes],
        )

        # Check that No Response category is created even if not connected
        last_wait_node = nodes[12]
        self.assertEqual(
            "No Response", last_wait_node["router"]["categories"][-1]["name"]
        )

        # TODO: Ideally, there should be more explicit tests here.
        # At least the functionality is covered by the integration tests simulating the
        # flow.

        render_ui = output["_ui"]["nodes"]

        def f_uuid(i):
            return nodes[i]["uuid"]

        def f_uipos_dict(i):
            return render_ui[f_uuid(i)]["position"]

        def f_uipos(i):
            return (f_uipos_dict(i)["left"], f_uipos_dict(i)["top"])

        def f_uitype(i):
            return render_ui[f_uuid(i)]["type"]

        self.assertIn(f_uuid(0), render_ui)
        self.assertEqual((340, 0), f_uipos(0))
        self.assertEqual((360, 180), f_uipos(1))
        self.assertEqual((840, 1200), f_uipos(12))
        self.assertEqual((740, 300), f_uipos(13))
        self.assertEqual("wait_for_response", f_uitype(0))
        self.assertEqual("split_by_subflow", f_uitype(1))
        self.assertEqual("split_by_expression", f_uitype(2))
        self.assertEqual("split_by_contact_field", f_uitype(3))
        self.assertEqual("split_by_run_result", f_uitype(4))
        self.assertEqual("split_by_groups", f_uitype(5))
        self.assertEqual("wait_for_response", f_uitype(6))
        self.assertEqual("split_by_random", f_uitype(7))
        self.assertEqual("execute_actions", f_uitype(8))
        self.assertEqual("execute_actions", f_uitype(9))
        self.assertEqual("wait_for_response", f_uitype(12))

        # Ensure that wait_for_response cases are working as intended
        node6 = nodes[6]
        categories = node6["router"]["categories"]
        self.assertEqual(len(categories), 3)
        self.assertEqual(categories[0]["name"], "A")
        self.assertEqual(categories[1]["name"], "Other")
        self.assertEqual(categories[2]["name"], "No Response")
        self.assertEqual(len(node6["router"]["cases"]), 1)

    def test_groups_and_flows(self):
        # We check that references flows and group are assigned uuids consistently
        tiny_uuid = "00000000-acec-434f-bc7c-14c584fc4bc8"
        test_uuid = "8224bfe2-acec-434f-bc7c-14c584fc4bc8"
        other_uuid = "12345678-acec-434f-bc7c-14c584fc4bc8"
        test_group_dict = {"name": "test group", "uuid": test_uuid}
        other_group_dict = {"name": "other group", "uuid": other_uuid}
        tiny_flow_dict = {"name": "tiny_flow", "uuid": tiny_uuid}

        # Make a flow with a single group node (no UUIDs), and put it into new container
        node = BasicNode()
        node.add_action(
            AddContactGroupAction([Group("test group"), Group("other group")])
        )
        tiny_flow = FlowContainer("tiny_flow", uuid=tiny_uuid)
        tiny_flow.add_node(node)
        container = RapidProContainer(groups=[Group("other group", other_uuid)])
        container.add_flow(tiny_flow)

        # Add flow from sheet into container
        rows = [
            self.row_parser.parse_row(row)
            for row in get_dict_from_csv("input/groups_and_flows.csv")
        ]
        FlowParser(
            container,
            flow_name="groups_and_flows",
            sheet_parser=MockSheetParser(rows),
        ).parse()

        # Render also invokes filling in all the flow/group UUIDs
        output = container.render()

        # Ensure container groups are complete and have correct UUIDs
        self.assertIn(test_group_dict, output["groups"])
        self.assertIn(other_group_dict, output["groups"])
        # These UUIDs are inferred from the sheet/the container groups, respectively
        self.assertEqual(
            output["flows"][0]["nodes"][0]["actions"][0]["groups"],
            [test_group_dict, other_group_dict],
        )

        nodes = output["flows"][1]["nodes"]
        # This UUID appears only in a later occurrence of the group in the sheet
        self.assertEqual(nodes[0]["actions"][0]["groups"], [test_group_dict])
        # This UUID is missing from the sheet, but explicit in the flow definition
        self.assertEqual(nodes[1]["actions"][0]["flow"], tiny_flow_dict)
        # This UUID is explicit in the sheet
        self.assertEqual(nodes[2]["actions"][0]["groups"], [test_group_dict])
        # This UUID appears in a previous occurrence of the group in the sheet
        self.assertEqual(
            nodes[3]["router"]["cases"][0]["arguments"],
            [test_uuid, "test group"],
        )
        # This UUID was part of the groups in the container, but not in the sheet
        self.assertEqual(nodes[6]["actions"][0]["groups"], [other_group_dict])

        tiny_flow.uuid = "something else"
        with self.assertRaises(ValueError):
            # The enter_flow node has a different uuid than the flow
            container.validate()

        tiny_flow.uuid = tiny_uuid
        container.flows[1].nodes[2].actions[0].groups[0].uuid = "something else"
        with self.assertRaises(ValueError):
            # The group is referenced by 2 different UUIDs
            container.validate()


class TestBlocks(TestCase):

    def setUp(self) -> None:
        self.row_parser = RowParser(FlowRowModel, CellParser())

    def render_output(self, table, context=None):
        return (
            FlowParser(
                RapidProContainer(),
                "basic loop",
                (
                    table
                    if isinstance(table, tablib.Dataset)
                    else tablib.import_set(table, format="csv")
                ),
                context=context or {},
            )
            .parse()
            .render()
        )

    def assert_messages(self, output, expected, context=None):
        self.assertEqual(
            traverse_flow(output, context or Context()),
            list(zip(["send_msg"] * len(expected), expected)),
        )

    def assert_actions(self, output, expected, context=None):
        self.assertEqual(
            traverse_flow(output, context or Context()),
            expected,
        )


class TestWebhook(TestBlocks):

    def test_basic_webhook(self):
        table_data = (
            "row_id,type,from,message_text,webhook.url,webhook.method,webhook.headers,save_name\n"  # noqa: E501
            ",call_webhook,start,Webhook Body,http://localhost:49998/?cmd=success,GET,Authorization;Token AAFFZZHH|,webhook_result\n"  # noqa: E501
        )
        action_exp = {
            "type": "call_webhook",
            "body": "Webhook Body",
            "method": "GET",
            "url": "http://localhost:49998/?cmd=success",
            "headers": {"Authorization": "Token AAFFZZHH"},
            "result_name": "webhook_result",
        }

        output = self.render_output(table_data)

        node = output["nodes"][0]
        node["actions"][0].pop("uuid")
        self.assertEqual(node["actions"][0], action_exp)

    def test_webhook_default_args(self):
        table_data = (
            "row_id,type,from,message_text,webhook.url,webhook.method,webhook.headers,save_name\n"  # noqa: E501
            ",call_webhook,start,Webhook Body,http://localhost:49998/?cmd=success,,,webhook_result\n"  # noqa: E501
        )

        output = self.render_output(table_data)

        node = output["nodes"][0]
        self.assertEqual(node["actions"][0]["headers"], {})
        self.assertEqual(node["actions"][0]["method"], "POST")

    def test_webhook_connectivity(self):
        table = (
            "row_id,type,from,condition,message_text,webhook.url,webhook.method,webhook.headers,save_name\n"  # noqa: E501
            "0,call_webhook,start,,Webhook Body,URL,,,webhook_result\n"
            ",send_message,0,Success,Webhook Success,,,,\n"
            ",send_message,0,,Webhook Failure,,,,\n"
        )

        node = self.render_output(table)["nodes"][0]

        self.assertEqual(node["actions"][0]["headers"], {})
        self.assertEqual(node["actions"][0]["method"], "POST")

        # Also check that the connectivity is correct
        self.assert_actions(
            self.render_output(table),
            [
                ("call_webhook", "URL"),
                ("send_msg", "Webhook Success"),
            ],
            context=Context(inputs=["Success"]),
        )
        self.assert_actions(
            self.render_output(table),
            [
                ("call_webhook", "URL"),
                ("send_msg", "Webhook Failure"),
            ],
            context=Context(inputs=["Failure"]),
        )


class TestLoops(TestBlocks):

    def test_basic_loop(self):
        table = (
            "row_id,type,from,loop_variable,message_text\n"
            "1,begin_for,start,i,1;2;3\n"
            ",send_message,,,{{i}}. Some text\n"
            ",end_for,,,\n"
        )

        nodes = self.render_output(table)["nodes"]

        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0]["actions"][0]["type"], "send_msg")
        self.assertEqual(nodes[0]["actions"][0]["text"], "1. Some text")
        self.assertEqual(nodes[1]["actions"][0]["text"], "2. Some text")
        self.assertEqual(nodes[2]["actions"][0]["text"], "3. Some text")

        # Also check that the connectivity is correct
        self.assert_messages(
            self.render_output(table),
            ["1. Some text", "2. Some text", "3. Some text"],
        )

    def test_enumerate(self):
        table_data = (
            "row_id,type,from,loop_variable,message_text\n"
            "1,begin_for,start,text;i,A;B;C\n"
            ",send_message,,,{{i+1}}. {{text}}\n"
            ",end_for,,,\n"
        )
        render_output = self.render_output(table_data)
        nodes = render_output["nodes"]
        self.assertEqual(len(nodes), 3)
        self.assertEqual(nodes[0]["actions"][0]["type"], "send_msg")
        self.assertEqual(nodes[0]["actions"][0]["text"], "1. A")
        self.assertEqual(nodes[1]["actions"][0]["text"], "2. B")
        self.assertEqual(nodes[2]["actions"][0]["text"], "3. C")

    def test_skip_loop_when_list_is_empty(self):
        table = tablib.Dataset(
            ("send_message", "", "", "Start"),
            ("begin_for", "", "i", "{@ [] @}"),
            ("send_message", "", "", "{{ i }}"),
            ("end_for", "", "", ""),
            ("send_message", "", "", "End"),
            headers=("type", "from", "loop_variable", "message_text"),
        )
        self.assert_messages(
            self.render_output(table),
            ["Start", "End"],
        )

    def test_one_element_loop(self):
        table_data = (
            "row_id,type,from,loop_variable,message_text\n"
            "1,begin_for,start,i,label\n"
            ",send_message,,,{{i}}. Some text\n"
            ",end_for,,,\n"
        )
        render_output = self.render_output(table_data)
        nodes = render_output["nodes"]
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["actions"][0]["type"], "send_msg")
        self.assertEqual(nodes[0]["actions"][0]["text"], "label. Some text")

    def test_nested_loop(self):
        table = (
            "row_id,type,from,loop_variable,message_text\n"
            "1,begin_for,start,i,1;2\n"
            ",begin_for,,j,A;B\n"
            ",send_message,,,{{i}}{{j}}. Some text\n"
            ",end_for,,,\n"
            ",end_for,,,\n"
        )
        expected = [
            "1A. Some text",
            "1B. Some text",
            "2A. Some text",
            "2B. Some text",
        ]

        output = self.render_output(table)

        self.assert_messages(output, expected)

    def test_loop_within_other_nodes(self):
        table = (
            "row_id,type,from,loop_variable,message_text\n"
            "1,send_message,start,,Starting text\n"
            "2,begin_for,1,i,1;2\n"
            ",send_message,,,{{i}}. Some text\n"
            ",end_for,,,\n"
            ",send_message,,,Following text\n"
        )
        expected = [
            "Starting text",
            "1. Some text",
            "2. Some text",
            "Following text",
        ]

        output = self.render_output(table)

        self.assert_messages(output, expected)

    def test_nested_loop_with_other_nodes(self):
        table = (
            "row_id,type,from,loop_variable,message_text\n"
            "1,begin_for,start,i,1;2\n"
            ",begin_for,,j,A;B\n"
            ",send_message,,,{{i}}{{j}}. Some text\n"
            ",end_for,,,\n"
            ",send_message,,,End of inner loop\n"
            ",end_for,,,\n"
            ",send_message,,,End of outer loop\n"
        )
        expected = [
            "1A. Some text",
            "1B. Some text",
            "End of inner loop",
            "2A. Some text",
            "2B. Some text",
            "End of inner loop",
            "End of outer loop",
        ]

        output = self.render_output(table)

        self.assert_messages(output, expected)

    def test_loop_with_explicit_following_node(self):
        table = (
            "row_id,type,from,loop_variable,message_text\n"
            "2,begin_for,,i,1;2\n"
            ",send_message,,,{{i}}. Some text\n"
            ",end_for,,,\n"
            ",send_message,2,,Following text\n"
        )
        expected = ["1. Some text", "2. Some text", "Following text"]

        output = self.render_output(table)

        self.assert_messages(output, expected)

    def test_loop_with_goto(self):
        table = (
            "row_id,type,from,condition,loop_variable,message_text\n"
            "2,begin_for,start,,i,1;2\n"
            ",send_message,,,,{{i}}. Text\n"
            ",end_for,,,,\n"
            "3,wait_for_response,2,,,\n"
            ",go_to,3,hello,,2\n"
            ",send_message,3,,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["1. Text", "2. Text", "Following text"],
            Context(inputs=["goodbye"]),
        )

        self.assert_messages(
            self.render_output(table),
            ["1. Text", "2. Text", "1. Text", "2. Text", "Following text"],
            Context(inputs=["hello", "goodbye"]),
        )

    def test_loop_with_goto_into_middle_of_loop(self):
        table = (
            "row_id,type,from,condition,loop_variable,message_text\n"
            "2,begin_for,start,,i,1;2\n"
            "item{{i}},send_message,,,,{{i}}. Text\n"
            ",end_for,,,,\n"
            "3,wait_for_response,2,,,\n"
            ",go_to,3,hello,,item2\n"
            ",send_message,3,,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["1. Text", "2. Text", "Following text"],
            Context(inputs=["goodbye"]),
        )
        self.assert_messages(
            self.render_output(table),
            ["1. Text", "2. Text", "2. Text", "Following text"],
            Context(inputs=["hello", "goodbye"]),
        )

    def test_loop_over_object(self):
        class TestObj:
            def __init__(self, value):
                self.value = value

        context = {"test_objs": [TestObj("1"), TestObj("2"), TestObj("A")]}
        table = (
            "row_id,type,from,loop_variable,message_text\n"
            "2,begin_for,start,obj,{@test_objs@}\n"
            ",send_message,,,Value: {{obj.value}}\n"
            ",end_for,,,\n"
        )

        self.assert_messages(
            self.render_output(table, context),
            ["Value: 1", "Value: 2", "Value: A"],
        )

    def test_loop_over_range(self):
        table = (
            "row_id,type,from,loop_variable,message_text\n"
            "2,begin_for,,i,{@range(5)@}\n"
            ",send_message,,,{{i}}. Text\n"
            ",end_for,,,\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["0. Text", "1. Text", "2. Text", "3. Text", "4. Text"],
        )


class TestConditionals(TestBlocks):
    def test_block_within_other_nodes(self):
        table = (
            "row_id,type,from,message_text\n"
            ",send_message,start,Starting text\n"
            ",begin_block,,\n"
            ",send_message,,Some text\n"
            ",end_block,,\n"
            ",send_message,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Starting text", "Some text", "Following text"],
        )

    def test_block_with_explicit_from(self):
        table = (
            "row_id,type,from,message_text\n"
            ",send_message,start,Start\n"
            "X,begin_block,,\n"
            ",send_message,,Text 1\n"
            ",send_message,,Text 2\n"
            ",end_block,,\n"
            ",send_message,X,Following\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Start", "Text 1", "Text 2", "Following"],
        )

    def test_block_with_goto(self):
        table = (
            "row_id,type,from,condition,message_text\n"
            "2,begin_block,start,,\n"
            ",send_message,,,Some text\n"
            ",end_block,,,\n"
            "3,wait_for_response,2,,\n"
            ",go_to,3,hello,2\n"
            ",send_message,3,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Some text", "Following text"],
            Context(inputs=["goodbye"]),
        )
        self.assert_messages(
            self.render_output(table),
            ["Some text", "Some text", "Following text"],
            Context(inputs=["hello", "goodbye"]),
        )

    def test_basic_if(self):
        table = (
            "row_id,type,from,include_if,message_text\n"
            ",send_message,,,text1\n"
            ",send_message,,FALSE,text2\n"
            ",send_message,,something,text3\n"
            ",send_message,,False,text4\n"
            ",send_message,,{{1 == 0}},text5\n"
            ",send_message,,{@1 == 0@},text6\n"
            ",send_message,,{@1 == 1@},text7\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["text1", "text3", "text7"],
        )

    def test_excluded_block_within_other_nodes(self):
        table = (
            "row_id,type,from,include_if,message_text\n"
            ",send_message,start,,Starting text\n"
            ",begin_block,,FALSE,\n"
            ",send_message,,,Skipped text\n"
            ",send_message,,TRUE,Skipped text 2\n"  # Should be skipped anyway
            ",end_block,,,\n"
            ",send_message,,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Starting text", "Following text"],
        )

    def test_excluded_for_block(self):
        table = (
            "row_id,type,from,include_if,message_text\n"
            ",begin_for,,FALSE,1;2\n"  # No loop var; but it's not parsed anyway
            ",send_message,,,Skipped text\n"
            ",end_for,,,\n"
            ",send_message,,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Following text"],
        )

    def test_excluded_block_with_nested_stuff(self):
        table = (
            "row_id,type,from,include_if,message_text\n"
            ",begin_block,,FALSE,\n"
            ",begin_block,,,\n"
            ",send_message,,,Skipped text\n"
            ",begin_for,,,1;2;3\n"  # No loop var; but it's not parsed anyway
            ",send_message,,,{{i}}. Some text\n"
            ",end_for,,,\n"
            ",end_block,,,\n"
            ",begin_for,,,A;B\n"
            ",send_message,,,{{i}}. Some other text\n"
            ",end_for,,,\n"
            ",end_block,,,\n"
            ",send_message,,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Following text"],
        )


class TestMultiExitBlocks(TestBlocks):

    def test_split_by_value(self):
        table = (
            "row_id,type,from,condition,message_text\n"
            "X,begin_block,,,\n"
            "1,split_by_value,,,@my_field\n"
            ",send_message,1,Value,It has the value\n"
            ",end_block,,,\n"
            ",send_message,X,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["It has the value", "Following text"],
            Context(variables={"@my_field": "Value"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Following text"],
            Context(variables={"@my_field": "Other"}),
        )

    def test_split_by_value_hard_loose_exit(self):
        table = (
            "row_id,type,from,condition,message_text\n"
            "X,begin_block,,,\n"
            "1,split_by_value,,,@my_field\n"
            ",send_message,1,Value,It has the value\n"
            ",hard_exit,1,Value2,\n"
            ",loose_exit,1,Value3,\n"
            ",end_block,,,\n"
            ",send_message,X,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["It has the value", "Following text"],
            Context(variables={"@my_field": "Value"}),
        )
        self.assert_messages(
            self.render_output(table),
            [],
            Context(variables={"@my_field": "Value2"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Following text"],
            Context(variables={"@my_field": "Value3"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Following text"],
            Context(variables={"@my_field": "Other"}),
        )

    def test_wait_for_response(self):
        table = (
            "row_id,type,from,condition,message_text,no_response\n"
            "X,begin_block,,,,\n"
            "1,wait_for_response,,,,60\n"
            ",send_message,1,Value,It has the value,\n"
            ",send_message,1,No Response,No Response,\n"
            ",end_block,,,\n"
            ",send_message,1,,Other,\n"
            ",send_message,X,,Following text,\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["It has the value", "Following text"],
            Context(inputs=["Value"]),
        )
        self.assert_messages(
            self.render_output(table),
            ["No Response", "Following text"],
            Context(inputs=[None]),
        )
        self.assert_messages(
            self.render_output(table),
            ["Other"],
            Context(inputs=["Something else"]),
        )

    def test_wait_for_response_hard_exits(self):
        table = (
            "row_id,type,from,condition,message_text,no_response\n"
            "X,begin_block,,,,\n"
            "1,wait_for_response,,,,60\n"
            ",send_message,1,Value,It has the value,\n"
            ",hard_exit,,,,\n"
            ",send_message,1,No Response,No Response,\n"
            ",hard_exit,,,,\n"
            ",end_block,,,\n"
            ",send_message,X,,Following text,\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["It has the value"],
            Context(inputs=["Value"]),
        )
        self.assert_messages(
            self.render_output(table),
            ["No Response"],
            Context(inputs=[None]),
        )
        self.assert_messages(
            self.render_output(table),
            ["Following text"],
            Context(inputs=["Something else"]),
        )

    def test_enter_flow(self):
        table = (
            "row_id,type,from,condition,message_text\n"
            ",send_message,start,,Starting text\n"
            "X,begin_block,,,\n"
            "1,start_new_flow,,,Some_flow\n"
            ",send_message,1,completed,Completed\n"
            ",end_block,,,\n"
            ",send_message,X,,Following text\n"
        )

        self.assert_actions(
            self.render_output(table),
            [
                ("send_msg", "Starting text"),
                ("enter_flow", "Some_flow"),
                ("send_msg", "Completed"),
                ("send_msg", "Following text"),
            ],
            Context(inputs=["completed"]),
        )
        self.assert_actions(
            self.render_output(table),
            [
                ("send_msg", "Starting text"),
                ("enter_flow", "Some_flow"),
                ("send_msg", "Following text"),
            ],
            Context(inputs=["expired"]),
        )


class TestNoOpRow(TestBlocks):

    def test_basic_noop(self):
        table = (
            "row_id,type,from,message_text\n"
            ",send_message,,Start message\n"
            ",no_op,,\n"
            ",send_message,,End message\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Start message", "End message"],
        )

    def test_multientry_noop(self):
        table = (
            "row_id,type,from,condition,message_text\n"
            "1,wait_for_response,,,\n"
            "2,send_message,1,A,Text A\n"
            "3,send_message,1,,Other\n"
            ",no_op,2;3,,\n"
            ",send_message,,,End message\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Text A", "End message"],
            context=Context(inputs=["A"]),
        )
        self.assert_messages(
            self.render_output(table),
            ["Other", "End message"],
            context=Context(inputs=["something"]),
        )

    def test_multiexit_noop(self):
        table = (
            "row_id,type,from,condition_value,condition_variable,message_text\n"
            ",send_message,,,,Start message\n"
            "1,no_op,,,,\n"
            ",send_message,1,A,@field,Text A\n"
            ",send_message,1,,@field,Other\n"
            ",send_message,1,B,@field,Text B\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Start message", "Text A"],
            context=Context(variables={"@field": "A"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Start message", "Text B"],
            context=Context(variables={"@field": "B"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Start message", "Other"],
            context=Context(variables={"@field": "something"}),
        )

    def test_multiexit_noop2(self):
        # only two rows are swapped, compared to previous case
        table = (
            "row_id,type,from,condition_value,condition_variable,message_text\n"
            ",send_message,,,,Start message\n"
            "1,no_op,,,,\n"
            ",send_message,1,,@field,Other\n"
            ",send_message,1,A,@field,Text A\n"
            ",send_message,1,B,@field,Text B\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Start message", "Text A"],
            context=Context(variables={"@field": "A"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Start message", "Text B"],
            context=Context(variables={"@field": "B"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Start message", "Other"],
            context=Context(variables={"@field": "something"}),
        )

    def test_multientryexit_noop(self):
        # only two rows are swapped, compared to previous case
        table = (
            "row_id,type,from,condition_value,condition_variable,message_text\n"
            "1,wait_for_response,,,,\n"
            "2,send_message,1,A,,Text 1A\n"
            "3,send_message,1,,,Other\n"
            "4,no_op,2;3,,,\n"
            ",send_message,4,A,@field,Text 2A\n"
            ",send_message,4,,@field,Other\n"
            ",send_message,4,B,@field,Text 2B\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Text 1A", "Text 2A"],
            context=Context(inputs=["A"], variables={"@field": "A"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Text 1A", "Text 2B"],
            context=Context(inputs=["A"], variables={"@field": "B"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Text 1A", "Other"],
            context=Context(inputs=["A"], variables={"@field": "something"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Other", "Text 2A"],
            context=Context(inputs=["something"], variables={"@field": "A"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Other", "Text 2B"],
            context=Context(inputs=["something"], variables={"@field": "B"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Other", "Other"],
            context=Context(inputs=["something"], variables={"@field": "something"}),
        )

    def test_noop_in_block_loose(self):
        # only two rows are swapped, compared to previous case
        table = (
            "row_id,type,from,condition_value,condition_variable,message_text\n"
            "X,begin_block,,,,\n"
            ",send_message,,,,Start message\n"
            "1,no_op,,,,\n"
            ",end_block,,,,\n"
            ",send_message,,,,End message\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Start message", "End message"],
        )

    def test_noop_in_block_notloose(self):
        # only two rows are swapped, compared to previous case
        table = (
            "row_id,type,from,condition_value,condition_variable,message_text\n"
            "X,begin_block,,,,\n"
            ",send_message,,,,Start message\n"
            "1,no_op,,,,\n"
            ",send_message,,,,End message\n"
            ",end_block,,,,\n"
            ",send_message,,,,End message 2\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Start message", "End message", "End message 2"],
        )

    def test_noop_in_block2(self):
        # only two rows are swapped, compared to previous case
        table = (
            "row_id,type,from,condition_value,condition_variable,message_text\n"
            "X,begin_block,,,,\n"
            ",send_message,,,,Start message\n"
            "1,no_op,,,,\n"
            ",loose_exit,1,,@field,\n"
            ",hard_exit,1,A,@field,\n"
            ",loose_exit,1,B,@field,\n"
            ",end_block,,,,\n"
            ",send_message,,,,End Message\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Start message"],
            context=Context(variables={"@field": "A"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Start message", "End Message"],
            context=Context(variables={"@field": "B"}),
        )
        self.assert_messages(
            self.render_output(table),
            ["Start message", "End Message"],
            context=Context(variables={"@field": "something"}),
        )

    def test_multientry_block(self):
        table = (
            "row_id,type,from,condition,message_text\n"
            "1,wait_for_response,start,,\n"
            "2,send_message,1,A,Message A\n"
            "3,send_message,1,,Other\n"
            "X,begin_block,2;3,,\n"
            ",send_message,,,Some text 1\n"
            ",end_block,,,\n"
            ",send_message,,,Following text\n"
        )

        self.assert_messages(
            self.render_output(table),
            ["Message A", "Some text 1", "Following text"],
            context=Context(inputs=["A"]),
        )
        self.assert_messages(
            self.render_output(table),
            ["Other", "Some text 1", "Following text"],
            context=Context(inputs=["something"]),
        )


class TestFlowParser(TestCase):

    def assert_flow(self, filename, flow_name, context):
        # Generate a flow from sheet
        output_1 = (
            FlowParser(
                RapidProContainer(),
                flow_name,
                get_table_from_file(filename),
            )
            .parse()
            .render()
        )

        # Load the expected output flow
        with open(TESTS_ROOT / "output/all_test_flows.json", "r") as file:
            expected_flow = next(
                iter(
                    flow
                    for flow in json.load(file)["flows"]
                    if flow["name"] == flow_name
                )
            )

        # Ensure the generated flow and expected flow are functionally equivalent
        expected_actions = traverse_flow(expected_flow, copy.deepcopy(context))
        self.assertEqual(
            traverse_flow(output_1, copy.deepcopy(context)),
            expected_actions,
        )

        # Convert the expected output into a flow and then into a sheet
        new_rows = FlowContainer.from_dict(expected_flow).to_rows()

        # Now convert the sheet back into a flow
        output_2 = (
            FlowParser(
                RapidProContainer(),
                flow_name=flow_name,
                sheet_parser=MockSheetParser(new_rows),
            )
            .parse()
            .render()
        )

        # Ensure the new generated flow and expected flow are functionally equivalent
        self.assertEqual(
            traverse_flow(output_2, copy.deepcopy(context)),
            expected_actions,
        )

    def test_no_switch_nodes(self):
        self.assert_flow(
            "input/no_switch_nodes.csv",
            "no_switch_nodes",
            Context(),
        )

    def test_no_switch_nodes_without_row_ids(self):
        self.assert_flow(
            "input/no_switch_nodes_without_row_ids.csv",
            "no_switch_nodes",
            Context(),
        )

    def test_switch_nodes(self):
        self.assert_flow(
            "input/switch_nodes.csv",
            "switch_nodes",
            Context(inputs=["b", "expired", "Success"]),
        )
        self.assert_flow(
            "input/switch_nodes.csv",
            "switch_nodes",
            Context(inputs=["b", "expired", "Failure", "Success"]),
        )
        self.assert_flow(
            "input/switch_nodes.csv",
            "switch_nodes",
            Context(inputs=["a", "completed"], variables={"expression": "not a"}),
        )
        self.assert_flow(
            "input/switch_nodes.csv",
            "switch_nodes",
            Context(
                inputs=["a", "completed"],
                group_names=["wrong group"],
                variables={
                    "expression": "a",
                    "@contact.name": "a",
                    "@results.result_wfr": "a",
                },
            ),
        )
        self.assert_flow(
            "input/switch_nodes.csv",
            "switch_nodes",
            Context(
                inputs=["a", "completed", "other"],
                group_names=["test group"],
                variables={
                    "expression": "a",
                    "@contact.name": "a",
                    "@results.result_wfr": "a",
                },
            ),
        )
        self.assert_flow(
            "input/switch_nodes.csv",
            "switch_nodes",
            Context(
                inputs=["a", "completed", "a"],
                random_choices=[0],
                group_names=["test group"],
                variables={
                    "expression": "a",
                    "@contact.name": "a",
                    "@results.result_wfr": "a",
                },
            ),
        )
        self.assert_flow(
            "input/switch_nodes.csv",
            "switch_nodes",
            Context(
                inputs=["a", "completed", "a"],
                random_choices=[2],
                group_names=["test group"],
                variables={
                    "expression": "a",
                    "@contact.name": "a",
                    "@results.result_wfr": "a",
                },
            ),
        )
        self.assert_flow(
            "input/switch_nodes.csv",
            "switch_nodes",
            Context(
                inputs=["a", "completed", None, None],
                group_names=["test group"],
                variables={
                    "expression": "a",
                    "@contact.name": "a",
                    "@results.result_wfr": "a",
                },
            ),
        )

    def test_loop_from_start(self):
        self.assert_flow(
            "input/loop_from_start.csv",
            "loop_from_start",
            Context(inputs=["b"]),
        )

        self.assert_flow(
            "input/loop_from_start.csv",
            "loop_from_start",
            Context(inputs=["a", "b"]),
        )

    def test_rejoin(self):
        self.assert_flow(
            "input/rejoin.csv",
            "rejoin",
            Context(random_choices=[0]),
        )

        self.assert_flow(
            "input/rejoin.csv",
            "rejoin",
            Context(random_choices=[1]),
        )

        self.assert_flow(
            "input/rejoin.csv",
            "rejoin",
            Context(random_choices=[2]),
        )

    def test_loop_and_multiple_conditions(self):
        self.assert_flow(
            "input/loop_and_multiple_conditions.csv",
            "loop_and_multiple_conditions",
            Context(inputs=["adfgyh"], random_choices=[0]),
        )

        self.assert_flow(
            "input/loop_and_multiple_conditions.csv",
            "loop_and_multiple_conditions",
            Context(inputs=["other"], random_choices=[0]),
        )

        self.assert_flow(
            "input/loop_and_multiple_conditions.csv",
            "loop_and_multiple_conditions",
            Context(random_choices=[1]),
        )

        self.assert_flow(
            "input/loop_and_multiple_conditions.csv",
            "loop_and_multiple_conditions",
            Context(inputs=["other"], random_choices=[2]),
        )

        self.assert_flow(
            "input/loop_and_multiple_conditions.csv",
            "loop_and_multiple_conditions",
            Context(inputs=["b", "a"], random_choices=[2]),
        )

        self.assert_flow(
            "input/loop_and_multiple_conditions.csv",
            "loop_and_multiple_conditions",
            Context(inputs=["b", "b", "c"], random_choices=[2]),
        )
