import copy
import re

from rpft.logger.logger import get_logger, logging_context
from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation.flowparser import FlowParser
from rpft.rapidpro.models.containers import RapidProContainer


LOGGER = get_logger()


def name_to_id(name):
    return re.sub("[^a-z0-9]", "", name.lower())


def apply_to_all_str(obj, func, inplace=False):
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


def apply_prefix_renaming(survey_question, prefix):
    """
    For all variables which are created in this survey question,
    apply the prefix to its name.
    """
    survey_question.variable = prefix + survey_question.variable
    survey_question.completion_variable = prefix + survey_question.completion_variable
    for assg in survey_question.postprocessing.assignments:
        assg.variable = prefix + assg.variable


def apply_prefix_substitutions(survey_question, variables, prefix):
    """
    Wherever any of these variable appears in this survey (in a condition,
    message text or elsewhere), apply the prefix to it.
    """

    def replace_vars(s):
        for var in variables:
            s = re.sub(
                f"fields.{var}([^a-zA-Z0-9_]|$)",
                f"fields.{prefix}{var}\\1",
                s,
            )
        return s

    apply_to_all_str(survey_question, replace_vars, inplace=True)


def apply_shorthand_substitutions(survey_question, survey_id):
    """
    Wherever @answer appears, replace it with the variable of this
    survey question where the user answer is stored.
    """

    def replace_vars(s):
        s = s.replace("@answerid", f"{survey_question.variable}")
        s = s.replace("@answer", f"@fields.{survey_question.variable}")
        s = s.replace("@prefixid", f"sq_{survey_id}")
        s = s.replace("@prefix", f"@fields.sq_{survey_id}")
        return s

    apply_to_all_str(survey_question, replace_vars, inplace=True)


class Survey:
    def __init__(self, name, question_data_sheet, survey_config, logging_prefix=None):
        self.name = name
        self.survey_id = name_to_id(name)
        self.question_data_sheet = copy.deepcopy(question_data_sheet)
        self.survey_config = survey_config
        self.logging_prefix = logging_prefix

    def preprocess_data_rows(self):
        self.initialize_survey_variables()
        for row in self.question_data_sheet.rows.values():
            apply_shorthand_substitutions(row, self.survey_id)
            row.expiration_message = (
                row.expiration_message or self.survey_config.expiration_message
            )

        # Apply all prefix replacements
        variables = self.get_survey_variables()
        prefix = self.survey_config.variable_prefix
        for row in self.question_data_sheet.rows.values():
            if prefix:
                apply_prefix_renaming(row, prefix)
            apply_prefix_substitutions(row, variables, prefix)

    def get_survey_variables(self):
        """Get list of variables that are created in this survey."""

        variables = []
        for row in self.question_data_sheet.rows.values():
            variables += [row.variable, row.completion_variable]
            assignment_variables = [
                assg.variable for assg in row.postprocessing.assignments
            ]
            variables += assignment_variables
        return list(set(variables))

    def initialize_survey_variables(self):
        """Initialize empty variable names with defaults."""
        for row in self.question_data_sheet.rows.values():
            if not row.variable:
                question_id = name_to_id(row.ID)
                row.variable = f"sq_{self.survey_id}_{question_id}"
            if not row.completion_variable:
                row.completion_variable = f"{row.variable}_complete"


class SurveyParser:
    QUESTION_TEMPLATE_NAME = "template_survey_question_wrapper"
    SURVEY_TEMPLATE_NAME = "template_survey_wrapper"

    def __init__(self, content_index_parser):
        """
        Args:
            content_index_parser: a ContentIndexParser.

            This is required to have access to
            - data_sheets: Dict[str, DataSheet], and
            - template_sheets: Dict[str, TemplateSheet]
            so that we instatiate the appropriate templates with the desired
            data. We cannot store these directly here, because whenever the
            FlowParser encounters an insert_as_block statement, it needs access
            to the ContentIndexParser to find the data/template to create this
            block. It may be preferable to have a shared data class instead.
        """

        self.surveys = {}
        self.content_index_parser = content_index_parser

    def add_survey(self, name, data_sheet, survey_config, logging_prefix=""):
        with logging_context(logging_prefix):
            if name in self.surveys:
                LOGGER.warning(
                    f"Duplicate survey definition sheet '{name}'. "
                    "Overwriting previous definition."
                )
        self.surveys[name] = Survey(name, data_sheet, survey_config, logging_prefix)

    def delete_survey(self, name):
        self.surveys.pop(name, None)

    def parse_all(self, rapidpro_container=None):
        rapidpro_container = rapidpro_container or RapidProContainer()
        for name in self.surveys:
            self.parse_survey(name, rapidpro_container)
        return rapidpro_container

    def parse_survey(self, name, rapidpro_container=None):
        rapidpro_container = rapidpro_container or RapidProContainer()
        survey = self.surveys[name]
        survey.preprocess_data_rows()
        self.parse_survey_wrapper(survey, rapidpro_container)

        with logging_context(f"{survey.logging_prefix} | survey {name}"):
            for row in survey.question_data_sheet.rows.values():
                with logging_context(
                    f"{survey.logging_prefix} | survey {name} | question {row.ID}"
                ):
                    self.parse_question(row, name, rapidpro_container)
        return rapidpro_container

    def parse_question(self, row, survey_name, rapidpro_container=None):
        rapidpro_container = rapidpro_container or RapidProContainer()
        template_arguments = []
        template_sheet = self.content_index_parser.get_template_sheet(
            SurveyParser.QUESTION_TEMPLATE_NAME
        )
        context = self.content_index_parser.map_template_arguments_to_context(
            template_sheet.argument_definitions,
            template_arguments,
            dict(row),
        )

        flow_parser = FlowParser(
            rapidpro_container,
            f"survey - {survey_name} - question - {row.ID}",
            template_sheet.table,
            context=context,
            content_index_parser=self.content_index_parser,
        )

        flow_parser.parse()

        return rapidpro_container

    def parse_survey_wrapper(self, survey, rapidpro_container):
        context = {
            "questions": list(survey.question_data_sheet.rows.values()),
            "survey_name": survey.name,
            "survey_id": survey.survey_id,
        }
        template_arguments = []
        template_sheet = self.content_index_parser.get_template_sheet(
            SurveyParser.SURVEY_TEMPLATE_NAME
        )
        context = self.content_index_parser.map_template_arguments_to_context(
            template_sheet.argument_definitions,
            template_arguments,
            context,
        )

        flow_parser = FlowParser(
            rapidpro_container,
            f"survey - {survey.name}",
            template_sheet.table,
            context=context,
            content_index_parser=self.content_index_parser,
        )
        flow_parser.parse()
