import unittest

from rpft.parsers.creation.contentindexparser import ContentIndexParser
from rpft.parsers.creation.tagmatcher import TagMatcher
from rpft.parsers.sheets import CompositeSheetReader, CSVSheetReader, XLSXSheetReader
from tests import TESTS_ROOT
from tests.mocks import MockSheetReader
from tests.utils import Context, traverse_flow

# flake8: noqa: E501


def csv_join(*args):
    return "\n".join(args) + "\n"


class TestTemplate(unittest.TestCase):
    def compare_messages(self, render_output, flow_name, messages_exp, context=None):
        flow_found = False
        for flow in render_output["flows"]:
            if flow["name"] == flow_name:
                flow_found = True
                actions = traverse_flow(flow, context or Context())
                actions_exp = list(zip(["send_msg"] * len(messages_exp), messages_exp))
                self.assertEqual(actions, actions_exp)
        if not flow_found:
            self.assertTrue(
                False, msg=f'Flow with name "{flow_name}" does not exist in output.'
            )


class TestParsing(TestTemplate):
    def get_flow_names(self, render_output):
        return {flow["name"] for flow in render_output["flows"]}

    def test_basic_template_definition(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "template_definition,my_template,,,,,\n"
            "template_definition,my_template2,,,,,draft\n"
        )
        my_template = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Some text",
        )

        sheet_reader = MockSheetReader(ci_sheet, {"my_template": my_template})
        ci_parser = ContentIndexParser(sheet_reader)
        template_sheet = ci_parser.get_template_sheet("my_template")
        self.assertEqual(template_sheet.table[0][1], "send_message")
        self.assertEqual(template_sheet.table[0][3], "Some text")
        with self.assertRaises(KeyError):
            ci_parser.get_template_sheet("my_template2")

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

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader)
        template_sheet = ci_parser.get_template_sheet("my_template")
        self.assertEqual(template_sheet.table[0][3], "Some text")
        template_sheet = ci_parser.get_template_sheet("my_template2")
        self.assertEqual(template_sheet.table[0][3], "Other text")

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

        sheet_reader = MockSheetReader(ci_sheet, {"simpledata": simpledata})
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.simplemodel")
        datamodelA = ci_parser.get_data_sheet_row("simpledata", "rowA")
        datamodelB = ci_parser.get_data_sheet_row("simpledata", "rowB")
        self.assertEqual(datamodelA.value1, "1A")
        self.assertEqual(datamodelA.value2, "2A")
        self.assertEqual(datamodelB.value1, "1B")
        self.assertEqual(datamodelB.value2, "2B")

    def test_generate_flows(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "create_flow,my_template,nesteddata,row1,,,\n"
            "create_flow,my_template,nesteddata,row2,,,\n"
            "create_flow,my_basic_flow,,,,,\n"
            "data_sheet,nesteddata,,,,NestedRowModel,\n"
        )
        # The templates are instantiated implicitly with all data rows
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

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.nestedmodel")
        container = ci_parser.parse_all()
        render_output = container.render()
        self.compare_messages(render_output, "my_basic_flow", ["Some text"])
        self.compare_messages(
            render_output, "my_template - row1", ["Value1", "Happy1 and Sad1"]
        )
        self.compare_messages(
            render_output, "my_template - row2", ["Value2", "Happy2 and Sad2"]
        )

        sheet_reader = MockSheetReader(ci_sheet_alt, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.nestedmodel")
        container = ci_parser.parse_all()
        render_output = container.render()
        self.compare_messages(render_output, "my_basic_flow", ["Some text"])
        self.compare_messages(
            render_output, "my_template - row1", ["Value1", "Happy1 and Sad1"]
        )
        self.compare_messages(
            render_output, "my_template - row2", ["Value2", "Happy2 and Sad2"]
        )
        self.compare_messages(
            render_output, "my_template - row3", ["Value3", "Happy3 and Sad3"]
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

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader)
        container = ci_parser.parse_all()
        render_output = container.render()
        self.compare_messages(render_output, "my_template", ["Other text"])

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

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.nestedmodel")
        container = ci_parser.parse_all()
        render_output = container.render()
        self.compare_messages(
            render_output,
            "my_renamed_template - row1",
            ["Value1 ARG1 ARG2", "Happy1 and Sad1"],
        )
        self.compare_messages(
            render_output,
            "my_renamed_template - row2",
            ["Value2 ARG1 ARG2", "Happy2 and Sad2"],
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

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.nestedmodel")
        container = ci_parser.parse_all()
        render_output = container.render()
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
        self.compare_messages(
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

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.listmodel")
        container = ci_parser.parse_all()
        render_output = container.render()
        messages_exp = [
            "Some text",
            "Hello :)Nice to see you :)",
            "Intermission",
            "Nice to see you :)Bye :)",
        ]
        self.compare_messages(
            render_output,
            "my_basic_flow",
            messages_exp,
            Context(variables={"@field.mood": "happy"}),
        )
        messages_exp = [
            "Some text",
            "Hello :(Not nice to see you :(",
            "Intermission",
            "Not nice to see you :(Bye :(",
        ]
        self.compare_messages(
            render_output,
            "my_basic_flow",
            messages_exp,
            Context(variables={"@field.mood": "sad"}),
        )
        messages_exp = [
            "Some text",
            "HelloNice to see you",
            "Intermission",
            "Nice to see youBye",
        ]
        self.compare_messages(
            render_output,
            "my_basic_flow",
            messages_exp,
            Context(variables={"@field.mood": "something else"}),
        )

        messages_exp = [
            "Hello :)Bye :)",
        ]
        self.compare_messages(
            render_output,
            "my_template - row3",
            messages_exp,
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

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.listmodel")
        container = ci_parser.parse_all()
        render_output = container.render()
        messages_exp = [
            "value1 default2",
        ]
        self.compare_messages(render_output, "my_template_default", messages_exp)
        messages_exp = [
            "value1 value2",
        ]
        self.compare_messages(render_output, "my_template_explicit", messages_exp)

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

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.evalmodels")
        container = ci_parser.parse_all()
        render_output = container.render()
        messages_exp = [
            "hello",
            "yes",
        ]
        self.compare_messages(render_output, "flow - id1", messages_exp)
        messages_exp = [
            "hello",
        ]
        self.compare_messages(render_output, "flow - id2", messages_exp)

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
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.evalmodels")
        container = ci_parser.parse_all()
        render_output = container.render()
        self.assertEqual(
            self.get_flow_names(render_output),
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
        self.compare_messages(render_output, "flow-world", ["Hello World"])
        self.compare_messages(render_output, "flow-t1", ["Hello Tag1Only"])
        self.compare_messages(render_output, "flow-b1", ["Hello Bag1Only"])
        self.compare_messages(render_output, "flow-t2", ["Hello Tag2Only"])
        self.compare_messages(render_output, "flow-b2", ["Hello Bag2Only"])
        self.compare_messages(render_output, "flow-t1t2", ["Hello Tag1Tag2"])
        self.compare_messages(render_output, "flow-t1b2", ["Hello Tag1Bag2"])
        self.compare_messages(render_output, "flow-b1t2", ["Hello Bag1Tag2"])

        tag_matcher = TagMatcher(["1", "tag1"])
        ci_parser = ContentIndexParser(
            sheet_reader, "tests.datarowmodels.evalmodels", tag_matcher
        )
        container = ci_parser.parse_all()
        render_output = container.render()
        self.assertEqual(
            self.get_flow_names(render_output),
            {"flow-world", "flow-t1", "flow-t2", "flow-b2", "flow-t1t2", "flow-t1b2"},
        )

        tag_matcher = TagMatcher(["1", "tag1", "bag1"])
        ci_parser = ContentIndexParser(
            sheet_reader, "tests.datarowmodels.evalmodels", tag_matcher
        )
        container = ci_parser.parse_all()
        render_output = container.render()
        self.assertEqual(
            self.get_flow_names(render_output),
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

        tag_matcher = TagMatcher(["1", "tag1", "2", "tag2"])
        ci_parser = ContentIndexParser(
            sheet_reader, "tests.datarowmodels.evalmodels", tag_matcher
        )
        container = ci_parser.parse_all()
        render_output = container.render()
        self.assertEqual(
            self.get_flow_names(render_output),
            {"flow-world", "flow-t1", "flow-t2", "flow-t1t2"},
        )

        tag_matcher = TagMatcher(["5", "tag1", "bag1"])
        ci_parser = ContentIndexParser(
            sheet_reader, "tests.datarowmodels.evalmodels", tag_matcher
        )
        container = ci_parser.parse_all()
        render_output = container.render()
        self.assertEqual(
            self.get_flow_names(render_output),
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


class TestOperation(unittest.TestCase):
    def test_concat(self):
        # Concatenate two fresh sheets
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation.type\n"
            "data_sheet,simpleA;simpleB,,,simpledata,SimpleRowModel,concat\n"
        )
        self.check_concat(ci_sheet)

    def test_concat_implicit(self):
        # Concatenate two fresh sheets
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation.type\n"
            "data_sheet,simpleA;simpleB,,,simpledata,SimpleRowModel,\n"
        )
        self.check_concat(ci_sheet)

    def test_concat2(self):
        # Concatenate a fresh sheet with an existing sheet
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation.type\n"
            "data_sheet,simpleA,,,renamedA,SimpleRowModel,\n"
            "data_sheet,renamedA;simpleB,,,simpledata,SimpleRowModel,concat\n"
        )
        self.check_concat(ci_sheet)

    def test_concat3(self):
        # Concatenate two existing sheets
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation.type\n"
            "data_sheet,simpleA,,,renamedA,SimpleRowModel,\n"
            "data_sheet,simpleB,,,renamedB,SimpleRowModel,\n"
            "data_sheet,renamedA;renamedB,,,simpledata,SimpleRowModel,concat\n"
        )
        self.check_concat(ci_sheet)

    def check_concat(self, ci_sheet):
        simpleA = csv_join(
            "ID,value1,value2",
            "rowA,1A,2A",
        )
        simpleB = csv_join(
            "ID,value1,value2",
            "rowB,1B,2B",
        )
        sheet_dict = {
            "simpleA": simpleA,
            "simpleB": simpleB,
        }

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.simplemodel")
        datamodelA = ci_parser.get_data_sheet_row("simpledata", "rowA")
        datamodelB = ci_parser.get_data_sheet_row("simpledata", "rowB")
        self.assertEqual(datamodelA.value1, "1A")
        self.assertEqual(datamodelA.value2, "2A")
        self.assertEqual(datamodelB.value1, "1B")
        self.assertEqual(datamodelB.value2, "2B")

    def test_filter_fresh(self):
        # The filter operation is referencing a sheet new (not previously parsed) sheet
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,filter|expression;value2=='fruit'\n"
        )
        self.check_example1(ci_sheet)

    def test_filter_existing(self):
        # The filter operation is referencing a previously parsed sheet
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,,SimpleRowModel,\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,filter|expression;value2=='fruit'\n"
        )
        self.check_example1(ci_sheet, original="simpleA")

    def test_filter_existing_renamed(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,renamedA,SimpleRowModel,\n"
            "data_sheet,renamedA,,,simpledata,SimpleRowModel,filter|expression;value2=='fruit'\n"
        )
        self.check_example1(ci_sheet, original="renamedA")

    def check_example1(self, ci_sheet, original=None):
        exp_keys = ["rowA", "rowC"]
        rows = self.check_filtersort(ci_sheet, exp_keys, original)
        self.assertEqual(rows["rowA"].value1, "orange")
        self.assertEqual(rows["rowA"].value2, "fruit")
        self.assertEqual(rows["rowC"].value1, "apple")
        self.assertEqual(rows["rowC"].value2, "fruit")

    def check_filtersort(self, ci_sheet, exp_keys, original=None):
        simple = csv_join(
            "ID,value1,value2",
            "rowA,orange,fruit",
            "rowB,potato,root",
            "rowC,apple,fruit",
            "rowD,Manioc,root",
        )
        all_keys = ["rowA", "rowB", "rowC", "rowD"]
        sheet_dict = {
            "simpleA": simple,
        }

        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader, "tests.datarowmodels.simplemodel")

        # Ensure input data hasn't been modified
        if original:
            original_rows = ci_parser.get_data_sheet_rows(original)
            self.assertEqual(list(original_rows.keys()), all_keys)

        # Ensure output data is as expected
        rows = ci_parser.get_data_sheet_rows("simpledata")
        self.assertEqual(len(rows), len(exp_keys))
        self.assertEqual(list(rows.keys()), exp_keys)
        return rows

    def test_filter_fresh2(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,\"filter|expression;value1 in ['orange','apple']\"\n"
        )
        exp_keys = ["rowA", "rowC"]
        self.check_filtersort(ci_sheet, exp_keys)

    def test_filter_fresh3(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,filter|expression;value1.lower() > 'd'\n"
        )
        exp_keys = ["rowA", "rowB", "rowD"]
        self.check_filtersort(ci_sheet, exp_keys)

    def test_sort(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,sort|expression;value1.lower()\n"
        )
        exp_keys = ["rowC", "rowD", "rowA", "rowB"]
        rows = self.check_filtersort(ci_sheet, exp_keys)
        self.assertEqual(rows["rowA"].value1, "orange")
        self.assertEqual(rows["rowA"].value2, "fruit")
        self.assertEqual(rows["rowB"].value1, "potato")
        self.assertEqual(rows["rowC"].value1, "apple")
        self.assertEqual(rows["rowD"].value1, "Manioc")

    def test_sort_existing(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,,SimpleRowModel,\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,sort|expression;value1.lower()\n"
        )
        exp_keys = ["rowC", "rowD", "rowA", "rowB"]
        self.check_filtersort(ci_sheet, exp_keys, original="simpleA")

    def test_sort_descending(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,operation\n"
            "data_sheet,simpleA,,,simpledata,SimpleRowModel,sort|expression;value1.lower()|order;descending\n"
        )
        exp_keys = ["rowB", "rowA", "rowD", "rowC"]
        self.check_filtersort(ci_sheet, exp_keys)


class TestParseCampaigns(unittest.TestCase):
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
            ci_sheet, {"my_campaign": my_campaign, "my_basic_flow": my_basic_flow}
        )
        ci_parser = ContentIndexParser(sheet_reader)
        container = ci_parser.parse_all()
        render_output = container.render()
        self.assertEqual(render_output["campaigns"][0]["name"], "renamed_campaign")
        self.assertEqual(render_output["campaigns"][0]["group"]["name"], "My Group")
        event = render_output["campaigns"][0]["events"][0]
        self.assertEqual(event["offset"], 15)
        self.assertEqual(event["unit"], "H")
        self.assertEqual(event["event_type"], "F")
        self.assertEqual(event["delivery_hour"], -1)
        self.assertEqual(event["message"], None)
        self.assertEqual(
            event["relative_to"], {"label": "Created On", "key": "created_on"}
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

        sheet_reader = MockSheetReader(ci_sheet, {"my_campaign": my_campaign})
        ci_parser = ContentIndexParser(sheet_reader)
        container = ci_parser.parse_all()
        render_output = container.render()
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
        sheet_reader = MockSheetReader(ci_sheet, sheet_dict)
        ci_parser = ContentIndexParser(sheet_reader)
        container = ci_parser.parse_all()
        render_output = container.render()
        self.assertEqual(render_output["campaigns"][0]["name"], "my_campaign")
        event = render_output["campaigns"][0]["events"][0]
        self.assertEqual(event["delivery_hour"], 6)


class TestParseFromFile(TestTemplate):
    def setUp(self):
        self.input_dir = TESTS_ROOT / "input/example1"

    def compare_to_expected(self, render_output):
        self.compare_messages(render_output, "my_basic_flow", ["Some text"])
        self.compare_messages(
            render_output, "my_template - row1", ["Value1", "Happy1 and Sad1"]
        )
        self.compare_messages(
            render_output, "my_template - row2", ["Value2", "Happy2 and Sad2"]
        )
        self.assertEqual(render_output["campaigns"][0]["name"], "my_campaign")
        self.assertEqual(render_output["campaigns"][0]["group"]["name"], "My Group")
        self.assertEqual(
            render_output["campaigns"][0]["events"][0]["flow"]["name"], "my_basic_flow"
        )
        self.assertEqual(
            render_output["campaigns"][0]["events"][0]["flow"]["uuid"],
            render_output["flows"][2]["uuid"],
        )

    def check_example1(self, ci_parser):
        container = ci_parser.parse_all()
        render_output = container.render()
        self.compare_to_expected(render_output)

    def test_example1_csv(self):
        # Same test as test_generate_flows but with csvs
        sheet_reader = CSVSheetReader(self.input_dir / "csv_workbook")
        ci_parser = ContentIndexParser(sheet_reader, "tests.input.example1.nestedmodel")
        self.check_example1(ci_parser)

    def test_example1_csv_composite(self):
        # Same test as test_generate_flows but with csvs
        sheet_reader = CSVSheetReader(self.input_dir / "csv_workbook")
        reader = CompositeSheetReader([sheet_reader])
        ci_parser = ContentIndexParser(reader, "tests.input.example1.nestedmodel")
        self.check_example1(ci_parser)

    def test_example1_xlsx(self):
        # Same test as above
        sheet_reader = XLSXSheetReader(self.input_dir / "content_index.xlsx")
        ci_parser = ContentIndexParser(sheet_reader, "tests.input.example1.nestedmodel")
        self.check_example1(ci_parser)

    def test_example1_xlsx_composite(self):
        # Same test as above
        sheet_reader = XLSXSheetReader(self.input_dir / "content_index.xlsx")
        reader = CompositeSheetReader([sheet_reader])
        ci_parser = ContentIndexParser(reader, "tests.input.example1.nestedmodel")
        self.check_example1(ci_parser)


class TestMultiFile(TestTemplate):
    def check(self, ci_parser, flow_name, messages_exp):
        container = ci_parser.parse_all()
        render_output = container.render()
        self.compare_messages(render_output, flow_name, messages_exp)

    def test_minimal(self):
        self.run_minimal()

    def test_minimal_singleindex(self):
        self.run_minimal(True)

    def run_minimal(self, singleindex=False):
        ci_sheet1 = csv_join(
            "type,sheet_name",
            "create_flow,template",
        )
        ci_sheet2 = csv_join(
            "type,sheet_name",
            "template_definition,template",
        )
        template = csv_join(
            "row_id,type,from,message_text",
            ",send_message,start,Hello!",
        )
        sheet_dict2 = {
            "template": template,
        }
        sheet_reader1 = MockSheetReader(ci_sheet1, name="mock_1")

        sheet_reader2 = MockSheetReader(
            None if singleindex else ci_sheet2,
            sheet_dict2,
            name="mock_2",
        )

        self.check(
            ContentIndexParser(CompositeSheetReader([sheet_reader1, sheet_reader2])),
            "template",
            ["Hello!"],
        )

        self.check(
            ContentIndexParser(CompositeSheetReader([sheet_reader2, sheet_reader1])),
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
        ci_parser = ContentIndexParser(
            sheet_reader=CompositeSheetReader([sheet_reader1, sheet_reader2]),
            user_data_model_module_name="tests.datarowmodels.minimalmodel",
        )
        self.check(ci_parser, "template - a", ["hi georg"])
        self.check(ci_parser, "template - b", ["hi chiara"])

        ci_parser = ContentIndexParser(
            sheet_reader=CompositeSheetReader([sheet_reader2, sheet_reader1]),
            user_data_model_module_name="tests.datarowmodels.minimalmodel",
        )
        self.check(ci_parser, "template - a", ["hello georg"])
        self.check(ci_parser, "template - b", ["hello chiara"])
