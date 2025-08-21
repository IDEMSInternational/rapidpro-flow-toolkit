from typing import Set
from unittest import TestCase

from rpft.parsers.creation.contentindexparser import ContentIndexParser
from rpft.parsers.creation.tagmatcher import TagMatcher
from rpft.parsers.sheets import (
    CSVSheetReader,
    DatasetSheetReader,
    XLSXSheetReader,
)
from rpft.rapidpro.models.triggers import RapidProTriggerError
from rpft.rapidpro.simulation import Context, traverse_flow
from rpft.sources import SheetDataSource

from tablib import Dataset
from tests import TESTS_ROOT
from tests.mocks import MockSheetReader
from tests.utils import csv_join


class TestTemplate(TestCase):
    def assertFlowMessages(self, render_output, flow_name, messages_exp, context=None):
        flows = [flow for flow in render_output["flows"] if flow["name"] == flow_name]

        self.assertTrue(
            len(flows) > 0,
            msg=f'Flow with name "{flow_name}" does not exist in output.',
        )

        actions = traverse_flow(flows[0], context or Context())
        actions_exp = list(zip(["send_msg"] * len(messages_exp), messages_exp))

        self.assertEqual(actions, actions_exp)


class TestTemplateDefinition(TestCase):
    def setUp(self):
        template = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )
        self.sheet_data_dict = {
            "my_template": template,
            "my_template2": template,
        }

    def test_basic_template_definition(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "template_definition,my_template,,,,,\n"
            "template_definition,my_template2,,,,,draft\n"
        )
        self.parser = ContentIndexParser(
            SheetDataSource(
                [
                    MockSheetReader(
                        ci_sheet,
                        self.sheet_data_dict,
                    )
                ]
            )
        )

        self.assertTemplateDefinition()

    def test_ignore_template_definition(self):
        """
        Ensure that ignoring a template row does NOT remove the template
        """
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "template_definition,my_template,,,,,\n"
            "ignore_row,my_template,,,,,\n"
        )
        self.parser = ContentIndexParser(
            SheetDataSource(
                [
                    MockSheetReader(
                        ci_sheet,
                        self.sheet_data_dict,
                    )
                ]
            )
        )

        self.assertTemplateDefinition()

    def assertTemplateDefinition(self):
        template_sheet = self.parser.template_sheets["my_template"]

        self.assertEqual(template_sheet.table[0][1], "send_message")
        self.assertEqual(template_sheet.table[0][3], "Some text")
        with self.assertRaises(KeyError):
            self.parser.template_sheets["my_template2"]


class TestParsing(TestTemplate):
    def test_basic_nesting(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "template_definition,my_template,,,,,\n"
            "content_index,ci_sheet2,,,,,\n"
        )
        ci_sheet2 = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "template_definition,my_template2,,,,,\n"
        )
        my_template = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )
        my_template2 = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Other text",
        )
        sheet_dict = {
            "ci_sheet2": ci_sheet2,
            "my_template": my_template,
            "my_template2": my_template2,
        }
        ci_parser = ContentIndexParser(
            SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)])
        )

        self.assertEqual(
            ci_parser.template_sheets["my_template"].table[0][3],
            "Some text",
        )
        self.assertEqual(
            ci_parser.template_sheets["my_template2"].table[0][3],
            "Other text",
        )

    def test_basic_user_model(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "data_sheet,simpledata,,,,SimpleRowModel,\n"
        )
        simpledata = csv_join(
            "ID,value1,value2",
            "rowA,1A,2A",
            "rowB,1B,2B",
        )
        definition = ContentIndexParser(
            SheetDataSource([MockSheetReader(ci_sheet, {"simpledata": simpledata})]),
            "tests.datarowmodels.simplemodel",
        ).definition
        datamodelA = definition.get_data_sheet_row("simpledata", "rowA")
        datamodelB = definition.get_data_sheet_row("simpledata", "rowB")

        self.assertEqual(datamodelA.value1, "1A")
        self.assertEqual(datamodelA.value2, "2A")
        self.assertEqual(datamodelB.value1, "1B")
        self.assertEqual(datamodelB.value2, "2B")

    def test_flow_type(self):
        ci_sheet = (
            "type,sheet_name,new_name,data_model,options\n"
            "create_flow,my_basic_flow,,,\n"
            "create_flow,my_basic_flow,my_other_flow,,flow_type;messaging_background\n"
        )
        my_basic_flow = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )
        sheet_dict = {
            "my_basic_flow": my_basic_flow,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertEqual(len(render_output["flows"]), 2)
        self.assertEqual(render_output["flows"][0]["name"], "my_basic_flow")
        self.assertEqual(render_output["flows"][0]["type"], "messaging")
        self.assertEqual(render_output["flows"][1]["name"], "my_other_flow")
        self.assertEqual(render_output["flows"][1]["type"], "messaging_background")

    def test_ignore_flow_definition(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "create_flow,my_basic_flow,,,,,\n"
            "create_flow,my_basic_flow,,,my_renamed_basic_flow,,\n"
            "create_flow,my_basic_flow,,,my_renamed_basic_flow2,,\n"
            "ignore_row,my_basic_flow,,,,,\n"
            "ignore_row,my_renamed_basic_flow,,,,,\n"
        )
        my_basic_flow = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )
        sheet_dict = {
            "my_basic_flow": my_basic_flow,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertEqual(len(render_output["flows"]), 1)
        self.assertEqual(render_output["flows"][0]["name"], "my_renamed_basic_flow2")

    def test_ignore_templated_flow_definition(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "create_flow,my_template,nesteddata,,,,\n"
            "create_flow,my_template,nesteddata,,bulk_renamed,,\n"
            "create_flow,my_template,nesteddata,row1,row1_renamed,,\n"
            "create_flow,my_template,nesteddata,row2,row2_renamed,,\n"
            "create_flow,my_template,nesteddata,row2,,,\n"
            "ignore_row,my_template,,,,,\n"
            "ignore_row,row1_renamed,,,,,\n"
            "data_sheet,nesteddata,,,,NestedRowModel,\n"
        )
        nesteddata = (
            "ID,value1,custom_field.happy,custom_field.sad\n"
            "row1,Value1,Happy1,Sad1\n"
            "row2,Value2,Happy2,Sad2\n"
        )
        my_template = (
            "row_id,type,from,message_text\n"
            ",send_message,start,{{value1}}\n"
            ",send_message,,{{custom_field.happy}} and {{custom_field.sad}}\n"
        )
        sheet_dict = {
            "nesteddata": nesteddata,
            "my_template": my_template,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertEqual(len(render_output["flows"]), 3)
        self.assertFlowNamesEqual(
            render_output,
            {
                "bulk_renamed - row1",
                "bulk_renamed - row2",
                "row2_renamed - row2",
            },
        )

    def test_generate_flows(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "create_flow,my_template,nesteddata,row1,,,\n"
            "create_flow,my_template,nesteddata,row2,,,\n"
            "create_flow,my_basic_flow,,,,,\n"
            "data_sheet,nesteddata,,,,NestedRowModel,\n"
        )
        ci_sheet_alt = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "create_flow,my_template,nesteddata,,,,\n"
            "create_flow,my_basic_flow,,,,,\n"
            "data_sheet,nesteddata,,,,NestedRowModel,\n"
        )
        nesteddata = (
            "ID,value1,custom_field.happy,custom_field.sad\n"
            "row1,Value1,Happy1,Sad1\n"
            "row2,Value2,Happy2,Sad2\n"
            "row3,Value3,Happy3,Sad3\n"
        )
        my_template = (
            "row_id,type,from,message_text\n"
            ",send_message,start,{{value1}}\n"
            ",send_message,,{{custom_field.happy}} and {{custom_field.sad}}\n"
        )
        my_basic_flow = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )
        sheet_dict = {
            "nesteddata": nesteddata,
            "my_template": my_template,
            "my_basic_flow": my_basic_flow,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "my_basic_flow",
            ["Some text"],
        )
        self.assertFlowMessages(
            render_output,
            "my_template - row1",
            ["Value1", "Happy1 and Sad1"],
        )
        self.assertFlowMessages(
            render_output,
            "my_template - row2",
            ["Value2", "Happy2 and Sad2"],
        )

        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet_alt, sheet_dict)]),
                "tests.datarowmodels.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "my_basic_flow",
            ["Some text"],
        )
        self.assertFlowMessages(
            render_output,
            "my_template - row1",
            ["Value1", "Happy1 and Sad1"],
        )
        self.assertFlowMessages(
            render_output,
            "my_template - row2",
            ["Value2", "Happy2 and Sad2"],
        )
        self.assertFlowMessages(
            render_output,
            "my_template - row3",
            ["Value3", "Happy3 and Sad3"],
        )

    def test_duplicate_create_flow(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "create_flow,my_template,,,,,\n"
            "create_flow,my_template2,,,my_template,,\n"
        )
        my_template = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )
        my_template2 = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Other text",
        )
        sheet_dict = {
            "ci_sheet": ci_sheet,
            "my_template": my_template,
            "my_template2": my_template2,
        }
        render_output = (
            ContentIndexParser(SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]))
            .parse_all()
            .render()
        )

        self.assertFlowMessages(render_output, "my_template", ["Other text"])

    def test_bulk_flows_with_args(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,template_arguments,new_name,data_model,status\n"  # noqa: E501
            "template_definition,my_template,,,arg1;arg2,,,\n"
            "create_flow,my_template,nesteddata,,ARG1;ARG2,my_renamed_template,,\n"
            "data_sheet,nesteddata,,,,,NestedRowModel,\n"
        )
        nesteddata = (
            "ID,value1,custom_field.happy,custom_field.sad\n"
            "row1,Value1,Happy1,Sad1\n"
            "row2,Value2,Happy2,Sad2\n"
        )
        my_template = (
            "row_id,type,from,message_text\n"
            ",send_message,start,{{value1}} {{arg1}} {{arg2}}\n"
            ",send_message,,{{custom_field.happy}} and {{custom_field.sad}}\n"
        )
        sheet_dict = {
            "nesteddata": nesteddata,
            "my_template": my_template,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "my_renamed_template - row1",
            ["Value1 ARG1 ARG2", "Happy1 and Sad1"],
        )
        self.assertFlowMessages(
            render_output,
            "my_renamed_template - row2",
            ["Value2 ARG1 ARG2", "Happy2 and Sad2"],
        )

    def test_global_context(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,template_arguments,new_name,data_model,status\n"  # noqa: E501
            "create_flow,my_basic_flow,,,,,,\n"
            "globals,globals_sheet1,,,,,,\n"
            "globals,globals_sheet2,,,,,,\n"
            "data_sheet,minimaldata,,,,,NameModel,\n"
            "template_definition,my_template,,,message,,,\n"
            "create_flow,my_template,minimaldata,,Local message,,,\n"
        )
        my_basic_flow = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,{{globals.message}}",
            ",send_message,,{{globals['spaced id']}}",
        )
        globals_sheet1 = (
            "ID,value\n"
            "message,Goodbye\n"
            "spaced id,This is weird\n"
        )
        globals_sheet2 = (
            "ID,value\n"
            "message,Hello\n"
        )
        minimaldata = (
            "ID,name\n"
            "row1,Name1\n"
            "row2,Name2\n"
        )
        my_template = (
            "row_id,type,from,message_text\n"
            ",send_message,start,{{globals.message}} {{name}}\n"
            ",send_message,,{{message}}\n"
        )
        sheet_dict = {
            "minimaldata": minimaldata,
            "my_template": my_template,
            "my_basic_flow": my_basic_flow,
            "globals_sheet1": globals_sheet1,
            "globals_sheet2": globals_sheet2,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource(
                    [MockSheetReader(ci_sheet, sheet_dict)]
                ),
                "tests.datarowmodels.minimalmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "my_basic_flow",
            ["Hello", "This is weird"],
        )
        self.assertFlowMessages(
            render_output,
            "my_template - row1",
            ["Hello Name1", "Local message"],
        )

    def test_insert_as_block(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "template_definition,my_template,,,,,\n"
            "create_flow,my_basic_flow,,,my_renamed_basic_flow,,\n"
            "data_sheet,nesteddata,,,,NestedRowModel,\n"
        )
        nesteddata = (
            "ID,value1,custom_field.happy,custom_field.sad\n"
            "row1,Value1,Happy1,Sad1\n"
            "row2,Value2,Happy2,Sad2\n"
        )
        my_template = (
            "row_id,type,from,condition,message_text\n"
            ",send_message,start,,{{value1}}\n"
            "1,wait_for_response,,,\n"
            ",send_message,1,happy,I'm {{custom_field.happy}}\n"
            ",send_message,1,sad,I'm {{custom_field.sad}}\n"
            ",hard_exit,,,\n"
            ",send_message,1,,I'm something\n"
        )
        my_basic_flow = (
            "row_id,type,from,message_text,data_sheet,data_row_id\n"
            ",send_message,start,Some text,,\n"
            "1,insert_as_block,,my_template,nesteddata,row1\n"
            ",send_message,,Next message 1,,\n"
            ",insert_as_block,,my_template,nesteddata,row2\n"
            ",send_message,,Next message 2,,\n"
            ",go_to,,1,,\n"
        )
        sheet_dict = {
            "nesteddata": nesteddata,
            "my_template": my_template,
            "my_basic_flow": my_basic_flow,
        }
        messages_exp = [
            "Some text",
            "Value1",
            "I'm Happy1",
            "Next message 1",
            "Value2",
            "I'm something",
            "Next message 2",
            "Value1",
            "I'm Sad1",  # we're taking the hard exit now, leaving the flow.
        ]
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "my_renamed_basic_flow",
            messages_exp,
            Context(inputs=["happy", "else", "sad"]),
        )

    def test_insert_as_block_with_sheet_arguments(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,template_arguments,new_name,data_model,status\n"  # noqa: E501
            "template_definition,my_template,,,lookup;sheet|,,,\n"
            "create_flow,my_template,nesteddata,row3,string_lookup,,,\n"
            "create_flow,my_basic_flow,,,,,,\n"
            "data_sheet,nesteddata,,,,,ListRowModel,\n"
            "data_sheet,string_lookup,,,,,LookupRowModel,\n"
        )
        nesteddata = (
            "ID,messages.1,messages.2\n"
            "row1,hello,nicetosee\n"
            "row2,nicetosee,bye\n"
            "row3,hello,bye\n"
        )
        string_lookup = (
            "ID,happy,sad,neutral\n"
            "hello,Hello :),Hello :(,Hello\n"
            "bye,Bye :),Bye :(,Bye\n"
            "nicetosee,Nice to see you :),Not nice to see you :(,Nice to see you\n"
        )
        my_template = (
            "row_id,type,from,condition,message_text\n"
            "1,split_by_value,,,@field.mood\n"
            ",send_message,1,happy,{% for msg in messages %}{{lookup[msg].happy}}{% endfor %}\n"  # noqa: E501
            ",send_message,1,sad,{% for msg in messages %}{{lookup[msg].sad}}{% endfor %}\n"  # noqa: E501
            ",send_message,1,,{% for msg in messages %}{{lookup[msg].neutral}}{% endfor %}\n"  # noqa: E501
        )
        my_basic_flow = (
            "row_id,type,from,message_text,data_sheet,data_row_id,template_arguments\n"
            ",send_message,start,Some text,,,\n"
            ",insert_as_block,,my_template,nesteddata,row1,string_lookup\n"
            ",send_message,,Intermission,,,\n"
            ",insert_as_block,,my_template,nesteddata,row2,string_lookup\n"
        )
        sheet_dict = {
            "nesteddata": nesteddata,
            "my_template": my_template,
            "my_basic_flow": my_basic_flow,
            "string_lookup": string_lookup,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.listmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "my_basic_flow",
            [
                "Some text",
                "Hello :)Nice to see you :)",
                "Intermission",
                "Nice to see you :)Bye :)",
            ],
            Context(variables={"@field.mood": "happy"}),
        )
        self.assertFlowMessages(
            render_output,
            "my_basic_flow",
            [
                "Some text",
                "Hello :(Not nice to see you :(",
                "Intermission",
                "Not nice to see you :(Bye :(",
            ],
            Context(variables={"@field.mood": "sad"}),
        )
        self.assertFlowMessages(
            render_output,
            "my_basic_flow",
            [
                "Some text",
                "HelloNice to see you",
                "Intermission",
                "Nice to see youBye",
            ],
            Context(variables={"@field.mood": "something else"}),
        )
        self.assertFlowMessages(
            render_output,
            "my_template - row3",
            ["Hello :)Bye :)"],
            Context(variables={"@field.mood": "happy"}),
        )

    def test_insert_as_block_with_arguments(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,template_arguments,new_name,data_model,status\n"  # noqa: E501
            "template_definition,my_template,,,arg1|arg2;;default2,,,\n"
            "create_flow,my_template,,,value1,my_template_default,,\n"
            "create_flow,my_template,,,value1;value2,my_template_explicit,,\n"
        )
        my_template = (
            "row_id,type,from,condition,message_text\n"
            ",send_message,,,{{arg1}} {{arg2}}\n"
        )
        sheet_dict = {
            "my_template": my_template,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.listmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "my_template_default",
            ["value1 default2"],
        )
        self.assertFlowMessages(
            render_output,
            "my_template_explicit",
            ["value1 value2"],
        )

    def test_eval(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,template_arguments,status\n"  # noqa: E501
            "template_definition,flow,,,,,metadata;sheet|,\n"
            "data_sheet,content,,,,EvalContentModel,,\n"
            "data_sheet,metadata,,,,EvalMetadataModel,,\n"
            "create_flow,flow,content,,,,metadata,\n"
        )
        metadata = csv_join(
            "ID,include_if",
            "a,text",
        )
        flow = (
            '"row_id","type","from","loop_variable","include_if","message_text"\n'
            ',"send_message",,,,"hello"\n'
            ',"send_message",,,"{@metadata[""a""].include_if|eval == ""yes""@}","{{text}}"\n'  # noqa: E501
        )
        content = csv_join(
            "ID,text",
            "id1,yes",
            "id2,no",
        )
        sheet_dict = {
            "metadata": metadata,
            "content": content,
            "flow": flow,
        }
        render_output = (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]),
                "tests.datarowmodels.evalmodels",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(render_output, "flow - id1", ["hello", "yes"])
        self.assertFlowMessages(render_output, "flow - id2", ["hello"])

    def test_tags(self):
        ci_sheet = (
            "type,sheet_name,new_name,template_arguments,tags.1,tags.2\n"
            "template_definition,flow,,arg,,\n"
            "create_flow,flow,flow-world,World,,\n"
            "create_flow,flow,flow-t1,Tag1Only,tag1,\n"
            "create_flow,flow,flow-b1,Bag1Only,bag1,\n"
            "create_flow,flow,flow-t2,Tag2Only,,tag2\n"
            "create_flow,flow,flow-b2,Bag2Only,,bag2\n"
            "create_flow,flow,flow-t1t2,Tag1Tag2,tag1,tag2\n"
            "create_flow,flow,flow-t1b2,Tag1Bag2,tag1,bag2\n"
            "create_flow,flow,flow-b1t2,Bag1Tag2,bag1,tag2\n"
        )
        flow = (
            '"row_id","type","from","loop_variable","include_if","message_text"\n'
            ',"send_message",,,,"Hello {{arg}}"\n'
        )
        sheet_dict = {
            "flow": flow,
        }
        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        render_output = (
            ContentIndexParser(
                SheetDataSource([sheet_reader]), "tests.datarowmodels.evalmodels"
            )
            .parse_all()
            .render()
        )

        self.assertFlowNamesEqual(
            render_output,
            {
                "flow-world",
                "flow-t1",
                "flow-b1",
                "flow-t2",
                "flow-b2",
                "flow-t1t2",
                "flow-t1b2",
                "flow-b1t2",
            },
        )
        self.assertFlowMessages(render_output, "flow-world", ["Hello World"])
        self.assertFlowMessages(render_output, "flow-t1", ["Hello Tag1Only"])
        self.assertFlowMessages(render_output, "flow-b1", ["Hello Bag1Only"])
        self.assertFlowMessages(render_output, "flow-t2", ["Hello Tag2Only"])
        self.assertFlowMessages(render_output, "flow-b2", ["Hello Bag2Only"])
        self.assertFlowMessages(render_output, "flow-t1t2", ["Hello Tag1Tag2"])
        self.assertFlowMessages(render_output, "flow-t1b2", ["Hello Tag1Bag2"])
        self.assertFlowMessages(render_output, "flow-b1t2", ["Hello Bag1Tag2"])

        self.assertFlowNamesEqual(
            ContentIndexParser(
                SheetDataSource([sheet_reader]),
                "tests.datarowmodels.evalmodels",
                TagMatcher(["1", "tag1"]),
            )
            .parse_all()
            .render(),
            {
                "flow-world",
                "flow-t1",
                "flow-t2",
                "flow-b2",
                "flow-t1t2",
                "flow-t1b2",
            },
        )

        self.assertFlowNamesEqual(
            ContentIndexParser(
                SheetDataSource([sheet_reader]),
                "tests.datarowmodels.evalmodels",
                TagMatcher(["1", "tag1", "bag1"]),
            )
            .parse_all()
            .render(),
            {
                "flow-world",
                "flow-t1",
                "flow-b1",
                "flow-t2",
                "flow-b2",
                "flow-t1t2",
                "flow-t1b2",
                "flow-b1t2",
            },
        )

        self.assertFlowNamesEqual(
            ContentIndexParser(
                SheetDataSource([sheet_reader]),
                "tests.datarowmodels.evalmodels",
                TagMatcher(["1", "tag1", "2", "tag2"]),
            )
            .parse_all()
            .render(),
            {
                "flow-world",
                "flow-t1",
                "flow-t2",
                "flow-t1t2",
            },
        )

        self.assertFlowNamesEqual(
            ContentIndexParser(
                SheetDataSource([sheet_reader]),
                "tests.datarowmodels.evalmodels",
                TagMatcher(["5", "tag1", "bag1"]),
            )
            .parse_all()
            .render(),
            {
                "flow-world",
                "flow-t1",
                "flow-b1",
                "flow-t2",
                "flow-b2",
                "flow-t1t2",
                "flow-t1b2",
                "flow-b1t2",
            },
        )

    def assertFlowNamesEqual(self, rapidpro_export: dict, flow_names: Set[str]):
        return self.assertEqual(
            {flow["name"] for flow in rapidpro_export["flows"]},
            flow_names,
        )


class TestOverrideBehaviour(TestCase):

    def test_data_defined_earlier_is_overridden_by_later_definitions(self):
        base = DatasetSheetReader(
            [
                Dataset(
                    ("A", "", ""),
                    ("B", "", ""),
                    headers=("ID", "value1", "value2"),
                    title="data",
                ),
                Dataset(
                    ("data_sheet", "data", "", "SimpleRowModel"),
                    headers=("type", "sheet_name", "new_name", "data_model"),
                    title="content_index",
                ),
            ],
            "base",
        )
        filter_ = DatasetSheetReader(
            [
                Dataset(
                    (
                        "data_sheet",
                        "data",
                        "data",
                        "SimpleRowModel",
                        'filter | expression ; ID != "B"',
                    ),
                    headers=(
                        "type",
                        "sheet_name",
                        "new_name",
                        "data_model",
                        "operation",
                    ),
                    title="content_index",
                )
            ],
            "filter",
        )
        deployment = DatasetSheetReader(
            [
                Dataset(
                    ("B", "", ""),
                    ("C", "", ""),
                    headers=("ID", "value1", "value2"),
                    title="data",
                ),
                Dataset(
                    ("data_sheet", "data", "data", "SimpleRowModel"),
                    headers=("type", "sheet_name", "new_name", "data_model"),
                    title="content_index",
                ),
            ],
            "deployment",
        )
        definition = ContentIndexParser(
            SheetDataSource([base, filter_, deployment]),
            "tests.datarowmodels.simplemodel",
        ).definition
        keys = list(definition.get_data_sheet_rows("data").keys())

        self.assertEqual(keys, ["B", "C"], "Deployment dataset should prevail")


class TestConcatOperation(TestCase):
    def setUp(self):
        simpleA = csv_join(
            "ID,value1,value2",
            "rowA,1A,2A",
        )
        simpleB = csv_join(
            "ID,value1,value2",
            "rowB,1B,2B",
        )
        self.sheet_dict = {
            "simpleA": simpleA,
            "simpleB": simpleB,
        }

    def test_two_fresh_sheets(self):
        self.ci_sheet = csv_join(
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation.type",
            "data_sheet,simpleA;simpleB,,,simpledata,SimpleRowModel,concat",
        )
        self.check_concat()

    def test_two_fresh_sheets_implictly(self):
        self.ci_sheet = csv_join(
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation.type",
            "data_sheet,simpleA;simpleB,,,simpledata,SimpleRowModel,",
        )
        self.check_concat()

    def test_fresh_and_existing_sheets(self):
        self.ci_sheet = csv_join(
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation.type",
            "data_sheet,simpleA,,,renamedA,SimpleRowModel,",
            "data_sheet,renamedA;simpleB,,,simpledata,SimpleRowModel,concat",
        )
        self.check_concat()

    def test_two_existing_sheets(self):
        self.ci_sheet = csv_join(
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation.type",
            "data_sheet,simpleA,,,renamedA,SimpleRowModel,\n"
            "data_sheet,simpleB,,,renamedB,SimpleRowModel,\n"
            "data_sheet,renamedA;renamedB,,,simpledata,SimpleRowModel,concat\n",
        )
        self.check_concat()

    def check_concat(self):
        definition = ContentIndexParser(
            SheetDataSource([MockSheetReader(self.ci_sheet, self.sheet_dict)]),
            "tests.datarowmodels.simplemodel",
        ).definition
        datamodelA = definition.get_data_sheet_row("simpledata", "rowA")
        datamodelB = definition.get_data_sheet_row("simpledata", "rowB")

        self.assertEqual(datamodelA.value1, "1A")
        self.assertEqual(datamodelA.value2, "2A")
        self.assertEqual(datamodelB.value1, "1B")
        self.assertEqual(datamodelB.value2, "2B")


class TestOperation(TestCase):
    def setUp(self):
        self.simple = csv_join(
            "ID,value1,value2",
            "rowA,orange,fruit",
            "rowB,potato,root",
            "rowC,apple,fruit",
            "rowD,Manioc,root",
        )

    def test_filter_fresh(self):
        # The filter operation is referencing a sheet new (not previously parsed) sheet
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,filter|expression;value2=='fruit'\n"  # noqa: E501
        )

        self.create_parser()

        self.assertRowsExistInOrder(["rowA", "rowC"])
        self.assertRowContent()

    def test_filter_existing(self):
        # The filter operation is referencing a previously parsed sheet
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,,SimpleRowModel,\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,filter|expression;value2=='fruit'\n"  # noqa: E501
        )

        self.create_parser()

        self.assertRowsExistInOrder(["rowA", "rowC"])
        self.assertRowContent()
        self.assertOriginalDataNotModified("simpleA")

    def test_filter_existing_renamed(self):
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,renamedA,SimpleRowModel,\n"
            "data_sheet,renamedA,,,simpledata,SimpleRowModel,filter|expression;value2=='fruit'\n"  # noqa: E501
        )
        self.create_parser()

        self.assertRowsExistInOrder(["rowA", "rowC"])
        self.assertRowContent()
        self.assertOriginalDataNotModified("renamedA")

    def test_filter_fresh2(self):
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,\"filter|expression;value1 in ['orange','apple']\"\n"  # noqa: E501
        )
        self.create_parser()

        self.assertRowsExistInOrder(["rowA", "rowC"])

    def test_filter_fresh3(self):
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,filter|expression;value1.lower() > 'd'\n"  # noqa: E501
        )

        self.create_parser()

        self.assertRowsExistInOrder(["rowA", "rowB", "rowD"])

    def test_sort(self):
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,sort|expression;value1.lower()\n"  # noqa: E501
        )

        self.create_parser()

        self.assertRowsExistInOrder(["rowC", "rowD", "rowA", "rowB"])
        rows = self.ci_parser.definition.get_data_sheet_rows("simpledata")
        self.assertEqual(rows["rowA"].value1, "orange")
        self.assertEqual(rows["rowA"].value2, "fruit")
        self.assertEqual(rows["rowB"].value1, "potato")
        self.assertEqual(rows["rowC"].value1, "apple")
        self.assertEqual(rows["rowD"].value1, "Manioc")

    def test_sort_existing(self):
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,,SimpleRowModel,\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,sort|expression;value1.lower()\n"  # noqa: E501
        )

        self.create_parser()

        self.assertRowsExistInOrder(["rowC", "rowD", "rowA", "rowB"])
        self.assertOriginalDataNotModified("simpleA")

    def test_sort_descending(self):
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,sort|expression;value1.lower()|order;descending\n"  # noqa: E501
        )

        self.create_parser()

        self.assertRowsExistInOrder(["rowB", "rowA", "rowD", "rowC"])

    def create_parser(self):
        self.ci_parser = ContentIndexParser(
            SheetDataSource([MockSheetReader(self.ci_sheet, {"simpleA": self.simple})]),
            "tests.datarowmodels.simplemodel",
        )

    def assertRowContent(self):
        rows = self.ci_parser.definition.get_data_sheet_rows("simpledata")

        self.assertEqual(rows["rowA"].value1, "orange")
        self.assertEqual(rows["rowA"].value2, "fruit")
        self.assertEqual(rows["rowC"].value1, "apple")
        self.assertEqual(rows["rowC"].value2, "fruit")

    def assertRowsExistInOrder(self, exp_keys):
        rows = self.ci_parser.definition.get_data_sheet_rows("simpledata")

        self.assertEqual(len(rows), len(exp_keys))
        self.assertEqual(list(rows.keys()), exp_keys)

    def assertOriginalDataNotModified(self, name):
        self.assertEqual(
            list(self.ci_parser.definition.get_data_sheet_rows(name).keys()),
            ["rowA", "rowB", "rowC", "rowD"],
        )


class TestModelInference(TestTemplate):
    def setUp(self):
        self.ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,status\n"
            "template_definition,my_template,,,\n"
            "create_flow,my_template,mydata,,\n"
            "data_sheet,mydata,,,\n"
        )
        self.my_template = (
            "row_id,type,from,message_text\n"
            ",send_message,start,Lst {{lst.0}} {{lst.1}}\n"
            ",send_message,,{{custom_field.happy}} and {{custom_field.sad}}\n"
        )

    def test_model_inference(self):
        self.mydata = (
            "ID,lst.1:int,lst.2:int,custom_field.happy,custom_field.sad\n"
            "row1,0,4,Happy1,Sad1\n"
            "row2,1,5,Happy2,Sad2\n"
        )

        flows = self.render_flows()

        self.assertFlows(flows)

    def test_model_inference_alt(self):
        self.mydata = (
            "ID,lst:List[int],custom_field.happy,custom_field.sad\n"
            "row1,0;4,Happy1,Sad1\n"
            "row2,1;5,Happy2,Sad2\n"
        )

        flows = self.render_flows()

        self.assertFlows(flows)

    def render_flows(self):
        sheet_dict = {
            "mydata": self.mydata,
            "my_template": self.my_template,
        }

        return (
            ContentIndexParser(
                SheetDataSource([MockSheetReader(self.ci_sheet, sheet_dict)])
            )
            .parse_all()
            .render()
        )

    def assertFlows(self, flows):
        self.assertFlowMessages(
            flows,
            "my_template - row1",
            ["Lst 0 4", "Happy1 and Sad1"],
        )
        self.assertFlowMessages(
            flows,
            "my_template - row2",
            ["Lst 1 5", "Happy2 and Sad2"],
        )


class TestParseCampaigns(TestCase):
    def test_parse_flow_campaign(self):
        ci_sheet = (
            "type,sheet_name,new_name,group\n"
            "create_campaign,my_campaign,renamed_campaign,My Group\n"
            "create_flow,my_basic_flow,,\n"
        )
        my_campaign = (
            "offset,unit,event_type,delivery_hour,message,relative_to,start_mode,flow\n"
            "15,H,F,,,Created On,I,my_basic_flow\n"
        )
        my_basic_flow = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )
        sheet_reader = MockSheetReader(
            ci_sheet,
            {
                "my_campaign": my_campaign,
                "my_basic_flow": my_basic_flow,
            },
        )

        render_output = (
            ContentIndexParser(SheetDataSource([sheet_reader])).parse_all().render()
        )

        self.assertEqual(render_output["campaigns"][0]["name"], "renamed_campaign")
        self.assertEqual(render_output["campaigns"][0]["group"]["name"], "My Group")
        event = render_output["campaigns"][0]["events"][0]
        self.assertEqual(event["offset"], 15)
        self.assertEqual(event["unit"], "H")
        self.assertEqual(event["event_type"], "F")
        self.assertEqual(event["delivery_hour"], -1)
        self.assertEqual(event["message"], None)
        self.assertEqual(
            event["relative_to"],
            {"label": "Created On", "key": "created_on"},
        )
        self.assertEqual(event["start_mode"], "I")
        self.assertEqual(event["flow"]["name"], "my_basic_flow")
        self.assertEqual(event["flow"]["uuid"], render_output["flows"][0]["uuid"])
        self.assertIsNone(event.get("base_language"))

    def test_parse_message_campaign(self):
        ci_sheet = csv_join(
            "type,sheet_name,new_name,group",
            "create_campaign,my_campaign,,My Group",
        )
        my_campaign = (
            "offset,unit,event_type,delivery_hour,message,relative_to,start_mode,flow\n"
            "150,D,M,12,Messagetext,Created On,I,\n"
        )

        render_output = (
            ContentIndexParser(
                SheetDataSource(
                    [MockSheetReader(ci_sheet, {"my_campaign": my_campaign})]
                )
            )
            .parse_all()
            .render()
        )

        self.assertEqual(render_output["campaigns"][0]["name"], "my_campaign")
        event = render_output["campaigns"][0]["events"][0]
        self.assertEqual(event["event_type"], "M")
        self.assertEqual(event["delivery_hour"], 12)
        self.assertEqual(event["message"], {"eng": "Messagetext"})
        self.assertEqual(event["base_language"], "eng")

    def test_duplicate_campaign(self):
        ci_sheet = (
            "type,sheet_name,new_name,group\n"
            "create_campaign,my_campaign,,My Group\n"
            "create_campaign,my_campaign2,my_campaign,My Group\n"
        )
        my_campaign = (
            "offset,unit,event_type,delivery_hour,message,relative_to,start_mode,flow\n"
            "150,D,M,12,Messagetext,Created On,I,\n"
        )
        my_campaign2 = (
            "offset,unit,event_type,delivery_hour,message,relative_to,start_mode,flow\n"
            "150,D,M,6,Messagetext,Created On,I,\n"
        )
        sheet_dict = {
            "my_campaign": my_campaign,
            "my_campaign2": my_campaign2,
        }

        render_output = (
            ContentIndexParser(SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]))
            .parse_all()
            .render()
        )

        self.assertEqual(render_output["campaigns"][0]["name"], "my_campaign")
        self.assertEqual(render_output["campaigns"][0]["events"][0]["delivery_hour"], 6)

    def test_ignore_campaign(self):
        ci_sheet = (
            "type,sheet_name,new_name,group\n"
            "create_campaign,my_campaign,,My Group\n"
            "create_campaign,my_campaign,my_renamed_campaign,My Group\n"
            "ignore_row,my_campaign,,\n"
        )
        my_campaign = (
            "offset,unit,event_type,delivery_hour,message,relative_to,start_mode,flow\n"
            "150,D,M,12,Messagetext,Created On,I,\n"
        )
        sheet_dict = {
            "my_campaign": my_campaign,
        }

        render_output = (
            ContentIndexParser(SheetDataSource([MockSheetReader(ci_sheet, sheet_dict)]))
            .parse_all()
            .render()
        )

        self.assertEqual(len(render_output["campaigns"]), 1)
        self.assertEqual(render_output["campaigns"][0]["name"], "my_renamed_campaign")


class TestParseTriggers(TestCase):
    def test_parse_triggers(self):
        ci_sheet = (
            "type,sheet_name\n"
            "create_triggers,my_triggers\n"
            "create_flow,my_basic_flow\n"
        )
        my_triggers = (
            "type,keywords,flow,groups,exclude_groups,match_type\n"
            "K,the word,my_basic_flow,My Group,,\n"
            "C,,my_basic_flow,My Group;Other Group,,\n"
            "M,,my_basic_flow,,My Group,\n"
            "K,first;second,my_basic_flow,,,F\n"
        )
        my_basic_flow = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )

        render_output = (
            ContentIndexParser(
                SheetDataSource(
                    [
                        MockSheetReader(
                            ci_sheet,
                            {
                                "my_triggers": my_triggers,
                                "my_basic_flow": my_basic_flow,
                            },
                        )
                    ]
                )
            )
            .parse_all()
            .render()
        )

        self.assertEqual(render_output["triggers"][0]["trigger_type"], "K")
        self.assertEqual(render_output["triggers"][1]["trigger_type"], "C")
        self.assertEqual(render_output["triggers"][2]["trigger_type"], "M")
        self.assertEqual(render_output["triggers"][0]["keywords"], ["the word"])
        self.assertEqual(render_output["triggers"][0]["keyword"], "the word")
        self.assertEqual(render_output["triggers"][1]["keywords"], [])
        self.assertIsNone(render_output["triggers"][1]["keyword"])
        self.assertEqual(render_output["triggers"][2]["keywords"], [])
        self.assertIsNone(render_output["triggers"][2]["keyword"])
        self.assertEqual(render_output["triggers"][3]["keywords"], ["first", "second"])
        self.assertEqual(render_output["triggers"][3]["keyword"], "first")
        self.assertEqual(render_output["triggers"][0]["match_type"], "F")
        self.assertEqual(render_output["triggers"][3]["match_type"], "F")
        for i in range(3):
            self.assertIsNone(render_output["triggers"][i]["channel"])
            self.assertEqual(
                render_output["triggers"][i]["flow"]["name"],
                "my_basic_flow",
            )
            self.assertEqual(
                render_output["triggers"][i]["flow"]["uuid"],
                render_output["flows"][0]["uuid"],
            )
        mygroup_uuid = render_output["groups"][0]["uuid"]
        groups0 = render_output["triggers"][0]["groups"]
        groups1 = render_output["triggers"][1]["groups"]
        groups2 = render_output["triggers"][2]["exclude_groups"]
        self.assertEqual(groups0[0]["name"], "My Group")
        self.assertEqual(groups0[0]["uuid"], mygroup_uuid)
        self.assertEqual(groups1[0]["name"], "My Group")
        self.assertEqual(groups1[0]["uuid"], mygroup_uuid)
        self.assertEqual(groups1[1]["name"], "Other Group")
        self.assertEqual(groups1[1]["uuid"], render_output["groups"][1]["uuid"])
        self.assertEqual(groups2[0]["name"], "My Group")
        self.assertEqual(groups2[0]["uuid"], mygroup_uuid)

    def test_parse_triggers_without_flow(self):
        ci_sheet = "type,sheet_name\n" "create_triggers,my_triggers\n"
        my_triggers = (
            "type,keywords,flow,groups,exclude_groups,match_type\n"
            "K,the word,my_basic_flow,My Group,,\n"
        )

        with self.assertRaises(RapidProTriggerError):
            ContentIndexParser(
                SheetDataSource(
                    [MockSheetReader(ci_sheet, {"my_triggers": my_triggers})]
                )
            ).parse_all().render()

    def test_ignore_triggers(self):
        ci_sheet = (
            "type,sheet_name\n"
            "create_triggers,my_triggers\n"
            "ignore_row,my_triggers\n"
        )
        my_triggers = (
            "type,keywords,flow,groups,exclude_groups,match_type\n"
            "K,the word,my_basic_flow,My Group,,\n"
        )
        my_basic_flow = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )

        render_output = (
            ContentIndexParser(
                SheetDataSource(
                    [
                        MockSheetReader(
                            ci_sheet,
                            {
                                "my_triggers": my_triggers,
                                "my_basic_flow": my_basic_flow,
                            },
                        )
                    ]
                )
            )
            .parse_all()
            .render()
        )

        self.assertEqual(len(render_output["triggers"]), 0)


class TestParseFromFile(TestTemplate):
    def setUp(self):
        self.input_dir = TESTS_ROOT / "input/example1"

    def test_example1_csv(self):
        flows = (
            ContentIndexParser(
                SheetDataSource([CSVSheetReader(self.input_dir / "csv_workbook")]),
                "tests.input.example1.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlows(flows)

    def test_example1_csv_composite(self):
        flows = (
            ContentIndexParser(
                SheetDataSource([CSVSheetReader(self.input_dir / "csv_workbook")]),
                "tests.input.example1.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlows(flows)

    def test_example1_xlsx(self):
        flows = (
            ContentIndexParser(
                SheetDataSource(
                    [XLSXSheetReader(self.input_dir / "content_index.xlsx")]
                ),
                "tests.input.example1.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlows(flows)

    def test_example1_xlsx_composite(self):
        flows = (
            ContentIndexParser(
                SheetDataSource(
                    [XLSXSheetReader(self.input_dir / "content_index.xlsx")]
                ),
                "tests.input.example1.nestedmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlows(flows)

    def assertFlows(self, flows):
        self.assertFlowMessages(
            flows,
            "my_basic_flow",
            ["Some text"],
        )
        self.assertFlowMessages(
            flows,
            "my_template - row1",
            ["Value1", "Happy1 and Sad1"],
        )
        self.assertFlowMessages(
            flows,
            "my_template - row2",
            ["Value2", "Happy2 and Sad2"],
        )
        self.assertEqual(
            flows["campaigns"][0]["name"],
            "my_campaign",
        )
        self.assertEqual(
            flows["campaigns"][0]["group"]["name"],
            "My Group",
        )
        self.assertEqual(
            flows["campaigns"][0]["events"][0]["flow"]["name"],
            "my_basic_flow",
        )
        self.assertEqual(
            flows["campaigns"][0]["events"][0]["flow"]["uuid"],
            flows["flows"][2]["uuid"],
        )


class TestMultiFile(TestTemplate):
    def test_minimal(self):
        ci_sheet = csv_join(
            "type,sheet_name",
            "template_definition,template",
        )
        self.run_minimal(ci_sheet)

    def test_minimal_singleindex(self):
        self.run_minimal(ci_sheet=None)

    def run_minimal(self, ci_sheet):
        ci_sheet1 = csv_join(
            "type,sheet_name",
            "create_flow,template",
        )
        template = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Hello!",
        )
        sheet_dict2 = {
            "template": template,
        }
        sheet_reader1 = MockSheetReader(ci_sheet1, name="mock_1")
        sheet_reader2 = MockSheetReader(ci_sheet, sheet_dict2, name="mock_2")

        self.assertFlowMessages(
            ContentIndexParser(
                SheetDataSource([sheet_reader1, sheet_reader2])
            )
            .parse_all()
            .render(),
            "template",
            ["Hello!"],
        )
        self.assertFlowMessages(
            ContentIndexParser(SheetDataSource([sheet_reader2, sheet_reader1]))
            .parse_all()
            .render(),
            "template",
            ["Hello!"],
        )

    def test_with_model(self):
        ci_sheet1 = (
            "type,sheet_name,data_sheet,data_model,status\n"
            "template_definition,template,,,\n"
            "data_sheet,names,,NameModel,draft\n"
            "create_flow,template,names,,\n"
        )
        ci_sheet2 = (
            "type,sheet_name,data_sheet,data_model,status\n"
            "data_sheet,names,,NameModel,\n"
            "template_definition,template,,,\n"
            "create_flow,template,names,,draft\n"
        )
        template1 = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,hello {{name}}",
        )
        template2 = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,hi {{name}}",
        )
        names = csv_join(
            "ID,name",
            "a,georg",
            "b,chiara",
        )
        names = "ID,name\n" "a,georg\n" "b,chiara\n"
        sheet_dict1 = {
            "template": template1,
            "names": names,
        }
        sheet_dict2 = {
            "template": template2,
        }
        sheet_reader1 = MockSheetReader(ci_sheet1, sheet_dict1, name="mock_1")
        sheet_reader2 = MockSheetReader(ci_sheet2, sheet_dict2, name="mock_2")

        flows = (
            ContentIndexParser(
                SheetDataSource([sheet_reader1, sheet_reader2]),
                user_data_model_module_name="tests.datarowmodels.minimalmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(flows, "template - a", ["hi georg"])
        self.assertFlowMessages(flows, "template - b", ["hi chiara"])

        flows = (
            ContentIndexParser(
                SheetDataSource([sheet_reader2, sheet_reader1]),
                user_data_model_module_name="tests.datarowmodels.minimalmodel",
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(flows, "template - a", ["hello georg"])
        self.assertFlowMessages(flows, "template - b", ["hello chiara"])
