import copy
from unittest import TestCase

from rpft.parsers.creation.contentindexparser import ContentIndexParser, DataSheet
from rpft.parsers.creation.commonmodels import (
    Assignment,
    Condition,
    ConditionsWithMessage,
    ConditionWithMessage,
)
from rpft.parsers.creation.globalrowmodels import SurveyQuestionRowModel
from rpft.parsers.creation.surveymodels import PostProcessing, SurveyConfig
from rpft.parsers.creation.surveyparser import (
    apply_variable_substitutions,
    apply_variable_renaming,
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
            ContentIndexParser(MockSheetReader(ci_sheet, {"survey_data": survey_data}))
            .parse_all()
            .render()
        )

        self.assertFlowMessages(
            render_output,
            "survey - survey_data - question - name",
            [
                ("send_msg", "Enter your name"),
                ("set_contact_field", "name"),
            ],
            Context(inputs=["My name"]),
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
            question="Previously you answered @fields.sq_s1_question1. "
            "Now answer Question 2:",
            relevant=[
                Condition(
                    value="4",
                    variable="@fields.sq_s1_question1",
                ),
                Condition(
                    value="5",
                    variable="@fields.sq_s1_question1b",
                ),
            ],
            postprocessing=PostProcessing(
                assignments=[
                    Assignment(
                        variable="new_variable",
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
            question="Previously you answered @fields.pre_sq_s1_question1. "
            "Now answer Question 2:",
            relevant=[
                Condition(
                    value="4",
                    variable="@fields.pre_sq_s1_question1",
                ),
                Condition(
                    value="5",
                    variable="@fields.sq_s1_question1b",
                ),
            ],
            postprocessing=PostProcessing(
                assignments=[
                    Assignment(
                        variable="pre_new_variable",
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
        apply_variable_renaming(question2_copy, prefix)
        apply_variable_substitutions(
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
            question="Tell us the answer to Question 1",
        )
        question1_replaced = SurveyQuestionRowModel(
            ID="question1",
            variable="pre_sq_s1_question1",
            completion_variable="pre_sq_s1_question1_complete",
            type="qtype",
            question="Tell us the answer to Question 1",
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
