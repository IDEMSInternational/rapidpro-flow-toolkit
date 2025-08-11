from unittest import TestCase

from rpft.parsers.creation.contentindexparser import (
    ContentIndexParser,
    DataSheet,
)
from rpft.parsers.creation.models import (
    Assignment,
    Condition,
    ConditionWithMessage,
    Message,
    PostProcessing,
    SurveyConfig,
)
from rpft.parsers.creation.globalrowmodels import SurveyQuestionRowModel
from rpft.parsers.creation.surveyparser import (
    apply_to_all_str,
    Survey,
    SurveyQuestion,
)
from rpft.parsers.sheets import CSVSheetReader
from rpft.rapidpro.simulation import Context, traverse_flow
from rpft.sources import SheetDataSource

from tests import TESTS_ROOT
from tests.mocks import MockSheetReader
from tests.utils import csv_join


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
        ci_sheet = csv_join(
            "type,sheet_name,data_model",
            "data_sheet,survey_data,SurveyQuestionRowModel",
        )
        survey_data = csv_join(
            "ID,type,question",
            "name,text,Enter your name",
            "else,text,Enter something else",
        )
        definition = ContentIndexParser(
            SheetDataSource([MockSheetReader(ci_sheet, {"survey_data": survey_data})])
        ).definition
        datamodelA = definition.get_data_sheet_row("survey_data", "name")
        datamodelB = definition.get_data_sheet_row("survey_data", "else")

        self.assertEqual(datamodelA.type, "text")
        self.assertEqual(datamodelA.messages[0].text, "Enter your name")
        self.assertEqual(datamodelB.type, "text")
        self.assertEqual(datamodelB.messages[0].text, "Enter something else")

    def test_basic_survey(self):
        ci_sheet = csv_join(
            "type,sheet_name,data_sheet,new_name,data_model",
            "data_sheet,survey_data,,,SurveyQuestionRowModel",
            "survey,,survey_data,Survey Name,",
        )
        survey_data = csv_join(
            "ID,type,question,variable,completion_variable,expiration.message",
            "first,text,First question?,first,first_complete,",
            "second,text,Second question?,second,second_complete,You waited too long",
            "third,text,Third question?,,,",
        )

        output = (
            ContentIndexParser(
                SheetDataSource(
                    [
                        CSVSheetReader(TESTS_ROOT / "input/survey_templates"),
                        MockSheetReader(ci_sheet, {"survey_data": survey_data}),
                    ],
                )
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name - question - first",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "First question?"),
                ("set_contact_field", "first"),
                ("set_contact_field", "first_complete"),
            ],
            Context(inputs=["First answer"]),
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name - question - third",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "Third question?"),
                ("set_contact_field", "sq_surveyname_third"),
                ("set_contact_field", "sq_surveyname_third_complete"),
            ],
            Context(inputs=["Third answer"]),
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name",
            [
                ("enter_flow", "survey - Survey Name - question - first"),
                ("enter_flow", "survey - Survey Name - question - second"),
                ("send_msg", "You waited too long"),
                ("set_run_result", "expired"),
            ],
            Context(inputs=["completed", "expired"]),
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name",
            [
                ("enter_flow", "survey - Survey Name - question - first"),
                ("enter_flow", "survey - Survey Name - question - second"),
                ("enter_flow", "survey - Survey Name - question - third"),
                ("set_run_result", "proceed"),
            ],
            Context(inputs=["completed", "completed", "completed"]),
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name",
            [
                ("enter_flow", "survey - Survey Name - question - first"),
            ],
            Context(inputs=["completed"], variables={"@child.results.stop": "yes"}),
        )

    def test_stop_condition(self):
        ci_sheet = csv_join(
            "type,sheet_name,data_sheet,data_row_id,new_name,data_model",
            "data_sheet,survey_data,,,,SurveyQuestionRowModel",
            "survey,,survey_data,,Survey Name,",
        )
        survey_data = csv_join(
            "ID,type,question,variable,completion_variable,stop.conditions.1.condition,stop.conditions.1.message,stop.conditions.2.condition,stop.conditions.2.message",  # noqa: E501
            "age,text,Enter your age,,,18|@answer|has_number_lt|,You are too young,25|@answer|has_number_gt|,You are too old",  # noqa: E501
            "name,text,Enter your name,,,,",
        )

        output = (
            ContentIndexParser(
                SheetDataSource(
                    [
                        CSVSheetReader(TESTS_ROOT / "input/survey_templates"),
                        MockSheetReader(ci_sheet, {"survey_data": survey_data}),
                    ]
                )
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            output,
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
            output,
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
            output,
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
            output,
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
        ci_sheet = csv_join(
            "type,sheet_name,data_sheet,new_name,data_model,template_arguments",
            "data_sheet,survey_data,,,SurveyQuestionRowModel,",
            "template_definition,template_survey_wrapper,,,,end_flow",
            "template_definition,template_survey_question_type_text,,,,",
            "survey,,survey_data,Survey Name,,my_end_flow",
        )
        survey_data = csv_join(
            "ID,type,question",
            "name,text,Enter your name",
        )
        template_survey_wrapper = csv_join(
            "type,from,message_text,condition",
            "send_message,start,Here's the survey,",
            "start_new_flow,,survey - {{survey_name}} - question - {{questions.0.ID}},",
            "start_new_flow,,{{end_flow}},Completed",
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
        output = (
            ContentIndexParser(
                SheetDataSource(
                    [
                        CSVSheetReader(TESTS_ROOT / "input/survey_templates"),
                        MockSheetReader(ci_sheet, sheet_dict),
                    ]
                )
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            output,
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
            output,
            "survey - Survey Name",
            [
                ("send_msg", "Here's the survey"),
                ("enter_flow", "survey - Survey Name - question - name"),
                ("enter_flow", "my_end_flow"),
            ],
            Context(inputs=["completed", "completed"]),
        )

    def test_template_arguments(self):
        ci_sheet = csv_join(
            "type,sheet_name,data_sheet,new_name,data_model,template_arguments",
            "data_sheet,survey_data,,,SurveyQuestionRowModel,",
            "survey,,survey_data,Survey Name,,survey_defaults",
        )
        survey_data = csv_join(
            "ID,type,question,variable,completion_variable",
            "first,text,First question?,first,",
            "second,text,Second question?,second,second_complete",
        )

        output = (
            ContentIndexParser(
                SheetDataSource(
                    [
                        CSVSheetReader(
                            TESTS_ROOT / "input/survey_templates_using_defaults"
                        ),
                        MockSheetReader(ci_sheet, {"survey_data": survey_data}),
                    ],
                )
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name - question - first",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "First question?"),
                ("send_msg", "Question level message"),
                ("set_contact_field", "first"),
                ("set_contact_field", "first_complete"),
            ],
            Context(inputs=["First answer"]),
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name",
            [
                ("enter_flow", "survey - Survey Name - question - first"),
                ("enter_flow", "survey - Survey Name - question - second"),
                ("send_msg", "Survey level message"),
            ],
            Context(inputs=["completed", "completed"]),
        )

    def test_create_question(self):
        ci_sheet = csv_join(
            "type,sheet_name,data_sheet,new_name,data_model,template_arguments,data_row_id",  # noqa: E501
            "data_sheet,survey_data,,,SurveyQuestionRowModel,,",
            "survey_question,,survey_data,Survey Name,,survey_defaults,first1",
            "survey_question,,survey_data,Survey Name,,survey_defaults,second2",
            "survey_question,,survey_data,Survey Name,,survey_defaults,third3",
        )
        survey_data = csv_join(
            "ID,type,question,variable,completion_variable",
            "first1,text,First question?,,",
            "second2,text,Second question?,second,",
            "third3,text,@answer question?,third,third_complete",
        )

        output = (
            ContentIndexParser(
                SheetDataSource(
                    [
                        CSVSheetReader(
                            TESTS_ROOT / "input/survey_templates_using_defaults"
                        ),
                        MockSheetReader(ci_sheet, {"survey_data": survey_data}),
                    ],
                )
            )
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name - question - first1",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "First question?"),
                ("send_msg", "Question level message"),
                ("set_contact_field", "sq_surveyname_first1"),
                ("set_contact_field", "sq_surveyname_first1_complete"),
            ],
            Context(inputs=["First answer"]),
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name - question - second2",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "Second question?"),
                ("send_msg", "Question level message"),
                ("set_contact_field", "second"),
                ("set_contact_field", "second_complete"),
            ],
            Context(inputs=["Second answer"]),
        )

        self.assertFlowMessages(
            output,
            "survey - Survey Name - question - third3",
            [
                ("set_run_result", "dummy"),
                ("send_msg", "@fields.third question?"),
                ("send_msg", "Question level message"),
                ("set_contact_field", "third"),
                ("set_contact_field", "third_complete"),
            ],
            Context(inputs=["Third answer"]),
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
                Condition(
                    value="7",
                    variable="custom_@surveyid_@questionid",
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
                Condition(
                    value="7",
                    variable="custom_s1_question2",
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
        )

        question2_copy = SurveyQuestion("Survey Name (unused)", question2)
        prefix = "pre_"
        question2_copy.apply_shorthand_substitutions("s1")
        question2_copy.apply_prefix_renaming(prefix)
        question2_copy.apply_prefix_substitutions(
            [
                "sq_s1_question1",
                "sq_s1_question1_complete",
                "sq_question2",
                "new_variable",
                "new_variable2",
            ],
            prefix,
        )

        self.assertEqual(question2_copy.data_row, question2_replaced)

        # Use this data in a survey
        question1 = SurveyQuestionRowModel(
            ID="question1",
            type="qtype",
            messages=[Message(text="Tell us the answer to Question 1")],
        )
        question1_replaced = SurveyQuestionRowModel(
            ID="question1",
            variable="pre_sq_s1_question1",
            completion_variable="pre_sq_s1_question1_complete",
            type="qtype",
            messages=[Message(text="Tell us the answer to Question 1")],
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
            survey.get_question_by_id("question1").data_row, question1_replaced
        )
        self.assertEqual(
            survey.get_question_by_id("question2").data_row, question2_replaced
        )
