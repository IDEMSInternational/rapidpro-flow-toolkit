import copy
from unittest import TestCase

from rpft.parsers.creation.contentindexparser import ContentIndexParser, DataSheet
from rpft.parsers.creation.models import (
    Assignment,
    Condition,
    ConditionsWithMessage,
    ConditionWithMessage,
    Message,
)
from rpft.parsers.creation.globalrowmodels import SurveyQuestionRowModel
from rpft.parsers.creation.surveymodels import PostProcessing, SurveyConfig
from rpft.parsers.creation.surveyparser import (
    apply_prefix_substitutions,
    apply_prefix_renaming,
    apply_shorthand_substitutions,
    apply_to_all_str,
    Survey,
)
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
        definition = ContentIndexParser(
            MockSheetReader(ci_sheet, {"survey_data": survey_data})
        ).definition
        datamodelA = definition.get_data_sheet_row("survey_data", "name")
        datamodelB = definition.get_data_sheet_row("survey_data", "else")

        self.assertEqual(datamodelA.type, "text")
        self.assertEqual(datamodelA.messages[0].text, "Enter your name")
        self.assertEqual(datamodelB.type, "text")
        self.assertEqual(datamodelB.messages[0].text, "Enter something else")

    def test_basic_survey(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "data_sheet,survey_data,,,,SurveyQuestionRowModel,\n"
            "create_survey,,survey_data,,Survey Name,,\n"
        )
        survey_data = csv_join(
            "ID,type,question,variable,completion_variable,expiration.message",
            "name,text,Enter your name,name,name_complete,",
            "else,text,Enter something else,else,else_complete,You waited too long",
            "age,text,Enter your age,,,",
        )

        render_output = (
            ContentIndexParser(MockSheetReader(ci_sheet, {"survey_data": survey_data}))
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name - question - name",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "Enter your name"),
                ("set_contact_field", "name"),
                ("set_contact_field", "name_complete"),
            ],
            Context(inputs=["My name"]),
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name - question - age",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "Enter your age"),
                ("set_contact_field", "sq_surveyname_age"),
                ("set_contact_field", "sq_surveyname_age_complete"),
            ],
            Context(inputs=["23"]),
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name",
            [
                ('enter_flow', 'survey - Survey Name - question - name'),
                ('enter_flow', 'survey - Survey Name - question - else'),
                ("send_msg", "You waited too long"),
                ("set_run_result", "expired"),
            ],
            Context(inputs=["completed", "expired"]),
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name",
            [
                ('enter_flow', 'survey - Survey Name - question - name'),
                ('enter_flow', 'survey - Survey Name - question - else'),
                ('enter_flow', 'survey - Survey Name - question - age'),
                ("set_run_result", "proceed"),
            ],
            Context(inputs=["completed", "completed", "completed"]),
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name",
            [
                ('enter_flow', 'survey - Survey Name - question - name'),
            ],
            Context(inputs=["completed"], variables={"@child.results.stop": "yes"}),
        )

    def test_stop_condition(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,status\n"
            "data_sheet,survey_data,,,,SurveyQuestionRowModel,\n"
            "create_survey,,survey_data,,Survey Name,,\n"
        )
        survey_data = csv_join(
            "ID,type,question,variable,completion_variable,stop.conditions.1.condition,stop.conditions.1.message,stop.conditions.2.condition,stop.conditions.2.message",  # noqa: E501
            "age,text,Enter your age,,,18|@answer|has_number_lt|,You are too young,25|@answer|has_number_gt|,You are too old",  # noqa: E501
            "name,text,Enter your name,,,,",
        )

        render_output = (
            ContentIndexParser(MockSheetReader(ci_sheet, {"survey_data": survey_data}))
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name - question - age",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "Enter your age"),
                ("set_contact_field", "sq_surveyname_age"),
                ("set_contact_field", "sq_surveyname_age_complete"),
                ("set_run_result", "stop"),
                ("send_msg", "You are too young"),
            ],
            Context(inputs=["15"], variables={"@fields.sq_surveyname_age": "15"}),
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name - question - name",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "Enter your name"),
                ("set_contact_field", "sq_surveyname_name"),
                ("set_contact_field", "sq_surveyname_name_complete"),
            ],
            Context(inputs=["21"]),
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name - question - age",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "Enter your age"),
                ("set_contact_field", "sq_surveyname_age"),
                ("set_contact_field", "sq_surveyname_age_complete"),
                ("set_run_result", "stop"),
                ("send_msg", "You are too old"),
            ],
            Context(inputs=["30"], variables={"@fields.sq_surveyname_age": "30"}),
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name - question - name",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "Enter your name"),
                ("set_contact_field", "sq_surveyname_name"),
                ("set_contact_field", "sq_surveyname_name_complete"),
            ],
            Context(inputs=["My name"]),
        )

    def test_template_overwrite(self):
        ci_sheet = (
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model,template_arguments,status\n"  # noqa: E501
            "data_sheet,survey_data,,,,SurveyQuestionRowModel,,\n"
            "template_definition,template_survey_wrapper,,,,,end_flow,\n"
            "template_definition,template_survey_question_type_text,,,,,,\n"
            "create_survey,,survey_data,,Survey Name,,my_end_flow,\n"
        )
        survey_data = csv_join(
            "ID,type,question",
            "name,text,Enter your name",
        )
        template_survey_wrapper = csv_join(
            "row_id,type,from,message_text,condition\n",
            ",send_message,start,Here's the survey,\n",
            ",start_new_flow,,survey - {{survey_name}} - question - {{questions.0.ID}},\n",  # noqa: E501
            ",start_new_flow,,{{end_flow}},Completed\n",
        )
        template_survey_question_type_text = csv_join(
            "row_id,type,from,message_text,save_name\n",
            ",send_message,start,Here's the question,\n",
            ",send_message,,{{messages.0.text}},\n",
            ",wait_for_response,,,input\n",
        )
        sheet_dict = {
            "survey_data": survey_data,
            "template_survey_wrapper": template_survey_wrapper,
            "template_survey_question_type_text": template_survey_question_type_text,
        }
        render_output = (
            ContentIndexParser(MockSheetReader(ci_sheet, sheet_dict))
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name - question - name",
            [
                ("send_msg", "Here's the question"),
                ("send_msg", "Enter your name"),
                ("set_contact_field", "sq_surveyname_name"),
                ("set_contact_field", "sq_surveyname_name_complete"),
            ],
            Context(inputs=["My name"]),
        )

        self.assertFlowMessages(
            render_output,
            "survey - Survey Name",
            [
                ("send_msg", "Here's the survey"),
                ("enter_flow", "survey - Survey Name - question - name"),
                ("enter_flow", "my_end_flow"),
            ],
            Context(inputs=["completed", "completed"]),
        )


class TestSurveyPreprocessing(TestCase):
    def test_apply_to_all_str(self):
        def f(s):
            return s.replace("a", "b")

        self.assertEqual(apply_to_all_str("a", f), "b")
        self.assertEqual(apply_to_all_str(["a", "name"], f), ["b", "nbme"])
        self.assertEqual(
            apply_to_all_str({"a": "name", "b": "ant"}, f), {"a": "nbme", "b": "bnt"}
        )
        self.assertEqual(
            apply_to_all_str({"a": "name", "b": "ant"}, f), {"a": "nbme", "b": "bnt"}
        )

        cond = ConditionWithMessage(
            condition=Condition(
                value="a",
                variable="abc",
            ),
            message="auto",
        )
        cond2 = ConditionWithMessage(
            condition=Condition(
                value="b",
                variable="bbc",
            ),
            message="buto",
        )
        self.assertEqual(apply_to_all_str(cond, f), cond2)

    def test_replacements(self):
        question2 = SurveyQuestionRowModel(
            ID="question2",
            type="qtype",
            variable="sq_question2",
            completion_variable="sq_question2_completion",
            messages=[
                Message(
                    text="Previously you answered @fields.sq_s1_question1. "
                    "Now answer Question 2:",
                )
            ],
            relevant=[
                Condition(
                    value="4",
                    variable="@fields.sq_s1_question1",
                ),
                Condition(
                    value="5",
                    variable="@fields.sq_s1_question1b",
                ),
                Condition(
                    value="6",
                    variable="@prefix_question0",
                ),
            ],
            postprocessing=PostProcessing(
                assignments=[
                    Assignment(
                        variable="@answerid_bucket",
                        value="@answer",
                    ),
                    Assignment(
                        variable="new_variable2",
                        value="@fields.sq_s1_question1",
                    ),
                ],
                flow="my_flow",
            ),
            confirmation=ConditionsWithMessage(
                conditions=[
                    ConditionWithMessage(
                        condition=Condition(
                            value="6",
                            variable="@(fields.sq_s1_question1"
                            " + fields.sq_s1_question1b)",
                        ),
                        message="Same as @fields.sq_s1_question1_new? "
                        "Or @fields.new_variable2?",
                    ),
                    ConditionWithMessage(
                        condition=Condition(
                            value="6",
                            variable="@fields.sq_s1_question1_complete",
                        ),
                        message="You entered @fields.sq_s1_question1. Confirm?",
                    ),
                ],
                message="You entered @answer but that's no good.",
            ),
        )

        question2_replaced = SurveyQuestionRowModel(
            ID="question2",
            type="qtype",
            variable="pre_sq_question2",
            completion_variable="pre_sq_question2_completion",
            messages=[
                Message(
                    text="Previously you answered @fields.pre_sq_s1_question1. "
                    "Now answer Question 2:",
                )
            ],
            relevant=[
                Condition(
                    value="4",
                    variable="@fields.pre_sq_s1_question1",
                ),
                Condition(
                    value="5",
                    variable="@fields.sq_s1_question1b",
                ),
                Condition(
                    value="6",
                    variable="@fields.sq_s1_question0",
                ),
            ],
            postprocessing=PostProcessing(
                assignments=[
                    Assignment(
                        variable="pre_sq_question2_bucket",
                        value="@fields.pre_sq_question2",
                    ),
                    Assignment(
                        variable="pre_new_variable2",
                        value="@fields.pre_sq_s1_question1",
                    ),
                ],
                flow="my_flow",
            ),
            confirmation=ConditionsWithMessage(
                conditions=[
                    ConditionWithMessage(
                        condition=Condition(
                            value="6",
                            variable="@(fields.pre_sq_s1_question1"
                            " + fields.sq_s1_question1b)",
                        ),
                        message="Same as @fields.sq_s1_question1_new? "
                        "Or @fields.pre_new_variable2?",
                    ),
                    ConditionWithMessage(
                        condition=Condition(
                            value="6",
                            variable="@fields.pre_sq_s1_question1_complete",
                        ),
                        message="You entered @fields.pre_sq_s1_question1. Confirm?",
                    ),
                ],
                message="You entered @fields.pre_sq_question2 but that's no good.",
            ),
        )

        question2_copy = copy.deepcopy(question2)
        prefix = "pre_"
        apply_shorthand_substitutions(question2_copy, "s1")
        apply_prefix_renaming(question2_copy, prefix)
        apply_prefix_substitutions(
            question2_copy,
            [
                "sq_s1_question1",
                "sq_s1_question1_complete",
                "sq_question2",
                "new_variable",
                "new_variable2",
            ],
            prefix,
        )

        self.assertEqual(question2_copy, question2_replaced)

        # Use this data in a survey
        question1 = SurveyQuestionRowModel(
            ID="question1",
            type="qtype",
            messages=[
                Message(text="Tell us the answer to Question 1")
            ]
        )
        question1_replaced = SurveyQuestionRowModel(
            ID="question1",
            variable="pre_sq_s1_question1",
            completion_variable="pre_sq_s1_question1_complete",
            type="qtype",
            messages=[
                Message(text="Tell us the answer to Question 1")
            ]
        )

        survey = Survey(
            "S 1~~",
            DataSheet(
                {"question1": question1, "question2": question2}, SurveyQuestionRowModel
            ),
            SurveyConfig(variable_prefix="pre_"),
        )
        survey.preprocess_data_rows()
        self.assertEqual(
            survey.question_data_sheet.rows["question1"], question1_replaced
        )
        self.assertEqual(
            survey.question_data_sheet.rows["question2"], question2_replaced
        )
