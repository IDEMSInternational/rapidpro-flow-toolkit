import copy
import re

from rpft.logger.logger import get_logger, logging_context
from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation import map_template_arguments
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
        self.question_data_sheet = copy.deepcopy(question_data_sheet)
        self.survey_config = survey_config
        self.logging_prefix = logging_prefix
        self.template_arguments = template_arguments or []

    def preprocess_data_rows(self):
        self.initialize_survey_variables()
        for row in self.question_data_sheet.rows.values():
            apply_shorthand_substitutions(row, self.survey_id)
            row.expiration.message = (
                row.expiration.message or self.survey_config.expiration_message
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

    def __init__(self, definition):
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
        self.definition = definition
        self.survey_template = definition.get_template(
            SurveyParser.SURVEY_TEMPLATE_NAME
        )
        self.question_template = definition.get_template(
            SurveyParser.QUESTION_TEMPLATE_NAME
        )

    @classmethod
    def parse_all(cls, definition, container: RapidProContainer):
        for survey in definition.surveys.values():
            SurveyParser(definition).parse_survey(survey, container)

        return container

    def parse_survey(self, survey: Survey, container: RapidProContainer):
        with logging_context(f"{survey.logging_prefix} | survey {survey.name}"):
            survey.preprocess_data_rows()
            self.parse_survey_wrapper(survey, container)

            for row in survey.question_data_sheet.rows.values():
                with logging_context(
                    f"{survey.logging_prefix}"
                    f" | survey {survey.name}"
                    f" | question {row.ID}"
                ):
                    self.parse_question(row, survey.name, container)

        return container

    def parse_question(self, row, survey_name, container: RapidProContainer):
        context = map_template_arguments(
            self.question_template.argument_definitions,
            [],
            dict(row),
            self.definition.data_sheets,
        )
        flow_parser = FlowParser(
            container,
            f"survey - {survey_name} - question - {row.ID}",
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
        context = {
            "questions": list(survey.question_data_sheet.rows.values()),
            "survey_name": survey.name,
            "survey_id": survey.survey_id,
        }
        context = map_template_arguments(
            self.survey_template.argument_definitions,
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
