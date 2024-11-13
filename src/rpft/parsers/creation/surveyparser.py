from rpft.logger.logger import get_logger, logging_context
from rpft.parsers.creation.flowparser import FlowParser
from rpft.rapidpro.models.containers import RapidProContainer

LOGGER = get_logger()


class Survey:
    def __init__(self, name, question_data_sheet, logging_prefix=None):
        self.name = name
        self.question_data_sheet = question_data_sheet
        self.logging_prefix = logging_prefix


class SurveyParser:
    QUESTION_TEMPLATE_NAME = "template_survey_question_wrapper"

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

    def add_survey(self, name, data_sheet, logging_prefix=""):
        with logging_context(logging_prefix):
            if name in self.surveys:
                LOGGER.warning(
                    f"Duplicate survey definition sheet '{name}'. "
                    "Overwriting previous definition."
                )
        self.surveys[name] = Survey(name, data_sheet, logging_prefix)

    def delete_survey(self, name):
        self.surveys.pop(name, None)

    def parse_all(self, rapidpro_container=None):
        rapidpro_container = rapidpro_container or RapidProContainer()
        for name in self.surveys:
            self.parse(name, rapidpro_container)
        return rapidpro_container

    def parse(self, name, rapidpro_container=None):
        rapidpro_container = rapidpro_container or RapidProContainer()
        survey = self.surveys[name]

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
