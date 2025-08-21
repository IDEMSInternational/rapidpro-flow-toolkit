import importlib
import logging
from collections import OrderedDict

from rpft.logger.logger import logging_context
from rpft.parsers.creation import globalrowmodels
from rpft.parsers.creation.campaigneventrowmodel import CampaignEventRowModel
from rpft.parsers.creation.campaignparser import CampaignParser
from rpft.parsers.creation.contentindexrowmodel import (
    ContentIndexRowModel,
    ContentIndexType,
)
from rpft.parsers.creation.flowparser import FlowParser
from rpft.parsers.creation.models import ChatbotDefinition, TemplateSheet
from rpft.parsers.creation.tagmatcher import TagMatcher
from rpft.parsers.creation.surveyparser import Survey, SurveyParser, SurveyQuestion
from rpft.parsers.creation.triggerparser import TriggerParser
from rpft.parsers.creation.triggerrowmodel import TriggerRowModel
from rpft.rapidpro.models.containers import RapidProContainer


LOGGER = logging.getLogger(__name__)


class DataSheet:
    def __init__(self, rows, row_model):
        """Args:
        rows: A dict mapping row_ids (str) to row_model instances.
        row_model: the model underlying the instances of rows.
        """
        self.rows = rows
        self.row_model = row_model

    def to_dict(self):
        return {
            "model": self.row_model.__name__,
            "rows": [content.model_dump() for content in self.rows.values()],
        }


class ParserError(Exception):
    pass


class ContentIndexParser:

    def __init__(
        self,
        data_source,
        user_data_model_module_name=None,
        tag_matcher=TagMatcher(),
    ):
        self.data_source = data_source
        self.tag_matcher = tag_matcher
        self.template_sheets = {}
        self.data_sheets = {}
        self.flow_definition_rows = []
        self.campaign_parsers: dict[str, tuple[str, CampaignParser]] = {}
        self.surveys = {}
        self.survey_questions: list[SurveyQuestion] = []
        self.trigger_parsers = OrderedDict()
        self.global_context = {}
        self.user_models_module = (
            importlib.import_module(user_data_model_module_name)
            if user_data_model_module_name
            else None
        )
        indices = self.data_source.get_all("content_index", ContentIndexRowModel)

        if not indices:
            raise Exception("No content index found")

        for entries, location, key in indices:
            self._process_content_index_table(entries, f"{location}-{key}")

        self._populate_missing_templates()
        self.definition = ChatbotDefinition(
            self.flow_definition_rows,
            self.data_sheets,
            self.template_sheets,
            self.surveys,
            self.survey_questions,
            {"globals": self.global_context},
        )

    def _process_content_index_table(self, rows, label):
        for row_idx, row in enumerate(rows, start=2):
            logging_prefix = f"{label} | row {row_idx}"

            with logging_context(logging_prefix):
                if row.status == "draft":
                    continue

                if not self.tag_matcher.matches(row.tags):
                    continue

                if len(row.sheet_name) != 1 and row.type not in [
                    ContentIndexType.DATA_SHEET.value,
                    ContentIndexType.SURVEY.value,
                    ContentIndexType.SURVEY_QUESTION.value,
                ]:
                    raise Exception(
                        f"For {row.type} rows, exactly one sheet_name has to be"
                        " specified"
                    )

                if row.type == ContentIndexType.CONTENT_INDEX.value:
                    entries, location, key = self.data_source.get(
                        row.sheet_name[0], ContentIndexRowModel
                    )

                    with logging_context(f"{key}"):
                        self._process_content_index_table(entries, f"{location}-{key}")
                elif row.type == ContentIndexType.DATA_SHEET.value:
                    if not len(row.sheet_name) >= 1:
                        raise Exception(
                            "For data_sheet rows, at least one sheet_name has to be"
                            " specified"
                        )

                    self._process_data_sheet(row)
                elif row.type == ContentIndexType.TEMPLATE.value:
                    if row.new_name:
                        LOGGER.warning(
                            "template_definition does not support 'new_name'; "
                            f"new_name '{row.new_name}' will be ignored."
                        )

                    self._add_template(row, True)
                elif row.type == ContentIndexType.FLOW.value:
                    self.flow_definition_rows.append((logging_prefix, row))
                elif row.type == ContentIndexType.CAMPAIGN.value:
                    campaign_parser = self.create_campaign_parser(row)
                    name = campaign_parser.campaign.name

                    if name in self.campaign_parsers:
                        LOGGER.debug(
                            f"Duplicate campaign definition sheet '{name}'. "
                            "Overwriting previous definition."
                        )

                    self.campaign_parsers[name] = (logging_prefix, campaign_parser)
                elif row.type == ContentIndexType.TRIGGERS.value:
                    self.trigger_parsers[row.sheet_name[0]] = (
                        logging_prefix,
                        self.create_trigger_parser(row),
                    )
                elif row.type == ContentIndexType.SURVEY.value:
                    self._add_survey(row, logging_prefix)
                elif row.type == ContentIndexType.SURVEY_QUESTION.value:
                    self._add_survey_question(row, logging_prefix)
                elif row.type == ContentIndexType.GLOBALS.value:
                    self._process_globals_sheet(row)
                elif row.type == ContentIndexType.IGNORE.value:
                    self._process_ignore_row(row.sheet_name[0])
                else:
                    LOGGER.error(f"invalid type: '{row.type}'")

    def _add_template(self, row, update_duplicates=False):
        sheet_name = row.sheet_name[0]

        if sheet_name in self.template_sheets and update_duplicates:
            LOGGER.debug(
                f"Duplicate template definition sheet '{sheet_name}'. "
                "Overwriting previous definition."
            )

        if sheet_name not in self.template_sheets or update_duplicates:
            sheet = self.data_source._get_sheet_or_die(sheet_name)
            self.template_sheets[sheet_name] = TemplateSheet(
                sheet_name,
                sheet.table,
                row.template_argument_definitions,
            )

    def _process_ignore_row(self, sheet_name):
        self.flow_definition_rows = [
            (logging_prefix, row)
            for logging_prefix, row in self.flow_definition_rows
            if (row.new_name or row.sheet_name[0]) != sheet_name
        ]
        self.campaign_parsers.pop(sheet_name, None)
        self.trigger_parsers.pop(sheet_name, None)
        self.surveys.pop(sheet_name, None)

    def _populate_missing_templates(self):
        for logging_prefix, row in self.flow_definition_rows:
            with logging_context(f"{logging_prefix} | {row.sheet_name[0]}"):
                self._add_template(row)

    def _process_globals_sheet(self, row):
        properties, *_ = self.data_source.get(
            row.sheet_name[0],
            globalrowmodels.IDValueRowModel,
        )
        context_dict = {r.ID: r.value for r in properties}
        intersection = self.global_context.keys() & context_dict.keys()
        if intersection:
            LOGGER.info(f"Overwriting globals {intersection}")
        self.global_context |= context_dict

    def _process_data_sheet(self, row):
        sheet_names = row.sheet_name

        if row.operation.type in ["filter", "sort"] and len(sheet_names) > 1:
            LOGGER.warning(
                "data_sheet definition take only one sheet_name for filter and sort "
                "operations. All but the first sheet_name are ignored."
            )

        if not row.operation.type:
            if len(sheet_names) > 1:
                LOGGER.warning(
                    "Implicitly concatenating data sheets without concat operation "
                    "is deprecated and may be removed in the future."
                )
                data_sheet = self._data_sheets_concat(sheet_names, row.data_model)
            else:
                data_sheet = self._get_new_data_sheet(sheet_names[0], row.data_model)

        else:
            if not row.new_name:
                raise Exception(
                    "If an operation is applied to a data_sheet, a new_name has to be"
                    " provided"
                )

            if row.operation.type == "concat":
                data_sheet = self._data_sheets_concat(sheet_names, row.data_model)
            elif row.operation.type == "filter":
                data_sheet = self._data_sheets_filter(
                    sheet_names[0], row.data_model, row.operation
                )
            elif row.operation.type == "sort":
                data_sheet = self._data_sheets_sort(
                    sheet_names[0], row.data_model, row.operation
                )
            else:
                raise Exception(f'Unknown operation "{row.operation}"')

        new_name = row.new_name or sheet_names[0]

        if new_name in self.data_sheets:
            LOGGER.debug(
                f"Duplicate data sheet {new_name}. Overwriting previous definition."
            )

        self.data_sheets[new_name] = data_sheet

    def _get_data_sheet(self, sheet_name, data_model_name):
        if sheet_name in self.data_sheets:
            return self.data_sheets[sheet_name]
        else:
            return self._get_new_data_sheet(sheet_name, data_model_name)

    def _get_new_data_sheet(self, sheet_name, data_model_name=None):
        model = (
            getattr(self.user_models_module, data_model_name, None)
            or getattr(globalrowmodels, data_model_name, None)
            if data_model_name
            else None
        )

        if data_model_name and not model:
            raise Exception(
                f'Undefined data_model_name "{data_model_name}" '
                f"in {self.user_models_module}."
            )

        with logging_context(sheet_name):
            items, *_ = self.data_source.get(sheet_name, model)
            model_instances = OrderedDict((item.ID, item) for item in items)

            return DataSheet(model_instances, model)

    def _data_sheets_concat(self, sheet_names, data_model_name):
        all_data_rows = OrderedDict()
        user_model = None

        for sheet_name in sheet_names:
            with logging_context(sheet_name):
                data_sheet = self._get_data_sheet(sheet_name, data_model_name)

                if user_model and user_model is not data_sheet.row_model:
                    raise Exception(
                        "Cannot concatenate data_sheets with different underlying"
                        " models"
                    )

                user_model = data_sheet.row_model
                all_data_rows.update(data_sheet.rows)

        return DataSheet(all_data_rows, user_model)

    def _data_sheets_filter(self, sheet_name, data_model_name, operation):
        data_sheet = self._get_data_sheet(sheet_name, data_model_name)
        new_row_data = OrderedDict()

        for row_id, row in data_sheet.rows.items():
            try:
                if eval(operation.expression, {}, dict(row)) is True:
                    new_row_data[row_id] = row
            except NameError as e:
                raise Exception(f"Invalid filtering expression: {e}")
            except SyntaxError as e:
                raise Exception(
                    f'Invalid filtering expression: "{e.text}". '
                    f"SyntaxError at line {e.lineno} character {e.offset}"
                )

        return DataSheet(new_row_data, data_sheet.row_model)

    def _data_sheets_sort(self, sheet_name, data_model_name, operation):
        data_sheet = self._get_data_sheet(sheet_name, data_model_name)

        try:
            new_row_data = OrderedDict(
                sorted(
                    data_sheet.rows.items(),
                    key=lambda kvpair: eval(operation.expression, {}, dict(kvpair[1])),
                    reverse=operation.order.lower() == "descending",
                )
            )
        except NameError as e:
            raise Exception(f"Invalid sorting expression: {e}")
        except SyntaxError as e:
            raise Exception(
                f'Invalid sorting expression: "{e.text}". '
                f"SyntaxError at line {e.lineno} character {e.offset}"
            )

        return DataSheet(new_row_data, data_sheet.row_model)

    def data_sheets_to_dict(self):
        sheets = {}

        for sheet_name, sheet in self.data_sheets.items():
            sheets[sheet_name] = sheet.to_dict()

        return {
            "sheets": sheets,
            "meta": {
                "user_models_module": self.user_models_module.__name__,
                "version": "0.1.0",
            },
        }

    def parse_all(self):
        rapidpro_container = RapidProContainer()
        self.parse_all_flows(rapidpro_container)
        self.parse_all_campaigns(rapidpro_container)
        self.parse_all_triggers(rapidpro_container)
        self.parse_all_surveys(rapidpro_container)

        return rapidpro_container

    def create_campaign_parser(self, row):
        sheet_name = row.sheet_name[0]
        rows, *_ = self.data_source.get(sheet_name, CampaignEventRowModel)

        return CampaignParser(row.new_name or sheet_name, row.group, rows)

    def create_trigger_parser(self, row):
        sheet_name = row.sheet_name[0]
        rows, *_ = self.data_source.get(sheet_name, TriggerRowModel)

        return TriggerParser(sheet_name, rows)

    def _add_survey(self, row, logging_prefix):
        name = row.new_name or row.data_sheet

        with logging_context(logging_prefix):
            if name in self.surveys:
                LOGGER.warning(
                    f"Duplicate survey definition sheet '{name}'. "
                    "Overwriting previous definition."
                )

        self.surveys[name] = Survey(
            name,
            self.data_sheets[row.data_sheet],
            row.survey_config,
            row.template_arguments,
            logging_prefix,
        )

    def _add_survey_question(self, row, logging_prefix):
        survey_name = row.new_name or row.data_sheet
        data_row = self.data_sheets[row.data_sheet].rows.get(row.data_row_id)
        if not data_row:
            with logging_context(logging_prefix):
                LOGGER.error(
                    f"No data_row_id given, or data_row_id '{row.data_row_id}' not"
                    f" present in survey question definition sheet '{row.data_sheet}'."
                    " Omitting survey question."
                )
            return

        self.survey_questions.append(
            SurveyQuestion(
                survey_name,
                data_row,
                row.template_arguments,
                logging_prefix,
            )
        )

    def parse_all_campaigns(self, rapidpro_container):
        for logging_prefix, campaign_parser in self.campaign_parsers.values():
            sheet_name = campaign_parser.campaign.name

            with logging_context(f"{logging_prefix} | {sheet_name}"):
                campaign = campaign_parser.parse()
                rapidpro_container.add_campaign(campaign)

    def parse_all_surveys(self, rapidpro_container):
        SurveyParser.parse_all(self.definition, rapidpro_container)

    def parse_all_triggers(self, rapidpro_container):
        for logging_prefix, trigger_parser in self.trigger_parsers.values():
            sheet_name = trigger_parser.sheet_name

            with logging_context(f"{logging_prefix} | {sheet_name}"):
                triggers = trigger_parser.parse()

                for trigger in triggers:
                    rapidpro_container.add_trigger(trigger)

    def parse_all_flows(self, rapidpro_container):
        FlowParser.parse_all(self.definition, rapidpro_container)
