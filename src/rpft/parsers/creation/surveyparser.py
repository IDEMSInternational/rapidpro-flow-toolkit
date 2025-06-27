import copy
import logging
import re

from rpft.logger.logger import logging_context
from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation import map_template_arguments
from rpft.parsers.creation.models import ChatbotDefinition
from rpft.parsers.creation.flowparser import FlowParser
from rpft.rapidpro.models.containers import RapidProContainer


LOGGER = logging.getLogger(__name__)


def name_to_id(name):
    return re.sub("[^a-z0-9]", "", name.lower())


def apply_to_all_str(obj, func, inplace=False):
    """
    Apply the given function to all string fields within the given nested model.

    `func` should accept a string as argument and return a string.
    """
    if isinstance(obj, str):
        return func(obj)
    elif isinstance(obj, dict):
        return {k: apply_to_all_str(v, func) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [apply_to_all_str(v, func) for v in obj]
    elif isinstance(obj, ParserModel):
        obj2 = obj if inplace else copy.deepcopy(obj)
        for k, v in obj.__dict__.items():
            setattr(obj2, k, apply_to_all_str(v, func))
        return obj2
    else:
        return obj


class SurveyQuestion:
    def __init__(
        self,
        survey_name,
        data_row,
        template_arguments=None,
        logging_prefix=None,
    ):
        self.data_row = copy.deepcopy(data_row)
        self.logging_prefix = logging_prefix
        self.template_arguments = template_arguments or []
        self.survey_name = survey_name
        self.survey_id = name_to_id(survey_name)
        self.question_id = name_to_id(self.data_row.ID)

    @property
    def ID(self):
        return self.data_row.ID

    def initialize_survey_variables(self, survey_id):
        """Initialize empty variable names with defaults."""
        if not self.data_row.variable:
            self.data_row.variable = f"sq_{survey_id}_{self.question_id}"
        if not self.data_row.completion_variable:
            self.data_row.completion_variable = f"{self.data_row.variable}_complete"

    def get_rapidpro_variables(self):
        """Get list of variables that are created in this survey."""
        return [
            self.data_row.variable,
            self.data_row.completion_variable,
        ] + [assg.variable for assg in self.data_row.postprocessing.assignments]

    def set_default_expiration_message(self, message):
        self.data_row.expiration.message = self.data_row.expiration.message or message

    def apply_prefix_renaming(self, prefix):
        """
        Apply a prefix to the names of all question variables.
        """
        self.data_row.variable = prefix + self.data_row.variable
        self.data_row.completion_variable = prefix + self.data_row.completion_variable
        for assg in self.data_row.postprocessing.assignments:
            assg.variable = prefix + assg.variable

    def apply_prefix_substitutions(self, variables, prefix):
        """
        Apply a prefix to the given question variables.

        Applies wherever any of these variables appear in the survey (condition, message
        text or elsewhere).
        """

        def replace_vars(s):
            for var in variables:
                s = re.sub(
                    f"fields.{var}([^a-zA-Z0-9_]|$)",
                    f"fields.{prefix}{var}\\1",
                    s,
                )
            return s

        apply_to_all_str(self.data_row, replace_vars, inplace=True)

    def apply_shorthand_substitutions(self, survey_id):
        """
        Replace placeholders, like '@answer', with actual values.
        """

        def replace_vars(s):
            s = s.replace("@answerid", f"{self.data_row.variable}")
            s = s.replace("@answer", f"@fields.{self.data_row.variable}")
            s = s.replace("@prefixid", f"sq_{survey_id}")
            s = s.replace("@prefix", f"@fields.sq_{survey_id}")
            s = s.replace("@surveyid", f"{survey_id}")
            s = s.replace("@questionid", f"{self.question_id}")
            return s

        apply_to_all_str(self.data_row, replace_vars, inplace=True)

    def populate_survey_variables(self, survey_id=None):
        """
        Initialize empty variable names with defaults and insert these in place of
        shorthand placeholders (e.g. @answer).
        """

        survey_id = survey_id or self.survey_id
        self.initialize_survey_variables(survey_id)
        self.apply_shorthand_substitutions(survey_id)


class Survey:
    def __init__(
        self,
        name,
        question_data_sheet,
        survey_config,
        template_arguments=None,
        logging_prefix=None,
    ):
        self.name = name
        self.survey_id = name_to_id(name)
        self.survey_config = survey_config
        self.logging_prefix = logging_prefix
        self.template_arguments = template_arguments or []
        self.questions = [
            SurveyQuestion(name, row, template_arguments, logging_prefix)
            for row in question_data_sheet.rows.values()
        ]

    def preprocess_data_rows(self):
        for question in self.questions:
            question.populate_survey_variables(self.survey_id)

        variables = self.get_rapidpro_variables()
        prefix = self.survey_config.variable_prefix

        for question in self.questions:
            question.set_default_expiration_message(
                self.survey_config.expiration_message
            )
            if prefix:
                question.apply_prefix_renaming(prefix)
            question.apply_prefix_substitutions(variables, prefix)

    def get_rapidpro_variables(self):
        """Get list of variables that are created in this survey."""
        variables = []
        for question in self.questions:
            variables += question.get_rapidpro_variables()
        return list(set(variables))

    def get_question_by_id(self, ID):
        for question in self.questions:
            if question.ID == ID:
                return question
        return None


class SurveyParser:
    QUESTION_TEMPLATE_NAME = "template_survey_question_wrapper"
    SURVEY_TEMPLATE_NAME = "template_survey_wrapper"

    def __init__(self, definition: ChatbotDefinition):
        self.definition = definition
        self.survey_template = definition.get_template(
            SurveyParser.SURVEY_TEMPLATE_NAME
        )
        self.question_template = definition.get_template(
            SurveyParser.QUESTION_TEMPLATE_NAME
        )

    @classmethod
    def parse_all(cls, definition, container: RapidProContainer):
        for survey_question in definition.survey_questions:
            SurveyParser(definition).parse_question(survey_question, container)
        for survey in definition.surveys.values():
            SurveyParser(definition).parse_survey(survey, container)

        return container

    def parse_survey(self, survey: Survey, container: RapidProContainer):
        with logging_context(f"{survey.logging_prefix} | survey {survey.name}"):
            survey.preprocess_data_rows()
            self.parse_survey_wrapper(survey, container)

            for question in survey.questions:
                with logging_context(
                    f"{survey.logging_prefix}"
                    f" | survey {survey.name}"
                    f" | question {question.ID}"
                ):
                    self.parse_question(question, container)

        return container

    def parse_question(self, question, container: RapidProContainer):
        question.populate_survey_variables()
        context = map_template_arguments(
            self.question_template,
            question.template_arguments,
            dict(question.data_row),
            self.definition.data_sheets,
        )
        flow_parser = FlowParser(
            container,
            f"survey - {question.survey_name} - question - {question.ID}",
            self.question_template.table,
            context=context,
            definition=self.definition,
        )

        flow_parser.parse()

        return container

    def parse_survey_wrapper(
        self,
        survey,
        container: RapidProContainer,
    ):
        question_data = [question.data_row for question in survey.questions]
        context = {
            "questions": question_data,
            "survey_name": survey.name,
            "survey_id": survey.survey_id,
        }
        context = map_template_arguments(
            self.survey_template,
            survey.template_arguments,
            context,
            self.definition.data_sheets,
        )
        flow_parser = FlowParser(
            container,
            f"survey - {survey.name}",
            self.survey_template.table,
            context=context,
            definition=self.definition,
        )
        flow_parser.parse()
