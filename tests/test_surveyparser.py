from unittest import TestCase

from rpft.parsers.creation.contentindexparser import ContentIndexParser
from tests.mocks import MockSheetReader
from tests.utils import Context, traverse_flow


def csv_join(*args):
    return "\n".join(args) + "\n"


class TestTemplate(TestCase):
    def assertFlowMessages(self, render_output, flow_name, actions_exp, context=None):
        flows = [flow for flow in render_output["flows"] if flow["name"] == flow_name]

        self.assertTrue(
            len(flows) > 0,
            msg=f'Flow with name "{flow_name}" does not exist in output.',
        )

        actions = traverse_flow(flows[0], context or Context())

        self.assertEqual(actions, actions_exp)


class TestSurveyParser(TestTemplate):
    def test_basic_global_model(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "data_sheet,survey_data,,,,SurveyQuestionRowModel,\n"
        )
        survey_data = csv_join(
            "ID,type,question",
            "name,text,Enter your name",
            "else,text,Enter something else",
        )
        ci_parser = ContentIndexParser(
            MockSheetReader(ci_sheet, {"survey_data": survey_data})
        )
        datamodelA = ci_parser.get_data_sheet_row("survey_data", "name")
        datamodelB = ci_parser.get_data_sheet_row("survey_data", "else")

        self.assertEqual(datamodelA.type, "text")
        self.assertEqual(datamodelA.question, "Enter your name")
        self.assertEqual(datamodelB.type, "text")
        self.assertEqual(datamodelB.question, "Enter something else")

    def test_basic_survey(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "data_sheet,survey_data,,,,SurveyQuestionRowModel,\n"
            "create_survey,survey_sheet,survey_data,,,,\n"
        )
        survey_data = csv_join(
            "ID,type,question,variable,completion_variable",
            "name,text,Enter your name,name,name_complete",
            "else,text,Enter something else,else,else_complete",
        )

        render_output = (
            ContentIndexParser(
                MockSheetReader(ci_sheet, {"survey_data": survey_data})
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "survey - survey_data - question - name",
            [
                ("send_msg", "Enter your name"),
                ('set_contact_field', 'name'),
            ],
            Context(inputs=["My name"])
        )
