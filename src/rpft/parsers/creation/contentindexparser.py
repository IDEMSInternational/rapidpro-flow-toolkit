import importlib
from collections import OrderedDict
from typing import Dict, List

from rpft.logger.logger import get_logger, logging_context
from rpft.parsers.common.model_inference import model_from_headers
from rpft.parsers.common.sheetparser import SheetParser
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
from rpft.parsers.creation.surveyparser import Survey, SurveyParser
from rpft.parsers.creation.triggerparser import TriggerParser
from rpft.parsers.creation.triggerrowmodel import TriggerRowModel
from rpft.parsers.sheets import Sheet
from rpft.rapidpro.models.containers import RapidProContainer

LOGGER = get_logger()


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
            "rows": [content.dict() for content in self.rows.values()],
        }


class ParserError(Exception):
    pass


class ContentIndexParser:

    def __init__(
        self,
        sheet_reader=None,
        user_data_model_module_name=None,
        tag_matcher=TagMatcher(),
    ):
        self.reader = sheet_reader
        self.tag_matcher = tag_matcher
        self.template_sheets = {}
        self.data_sheets = {}
        self.flow_definition_rows: List[ContentIndexRowModel] = []
        self.campaign_parsers: Dict[str, tuple[str, CampaignParser]] = {}
        self.surveys = {}
        self.trigger_parsers = OrderedDict()
        self.user_models_module = (
            importlib.import_module(user_data_model_module_name)
            if user_data_model_module_name
            else None
        )
        indices = self.reader.get_sheets_by_name("content_index")

        if not indices:
            LOGGER.critical("No content index sheet provided")

        for sheet in indices:
            self._process_content_index_table(sheet)

        self._populate_missing_templates()
        self.definition = ChatbotDefinition(
            self.flow_definition_rows,
            self.data_sheets,
            self.template_sheets,
            self.surveys,
        )

    def _process_content_index_table(self, sheet: Sheet):
        rows = SheetParser(sheet.table, ContentIndexRowModel).parse_all()

        for row_idx, row in enumerate(rows, start=2):
            logging_prefix = f"{sheet.reader.name}-{sheet.name} | row {row_idx}"

            with logging_context(logging_prefix):
                if row.status == "draft":
                    continue

                if not self.tag_matcher.matches(row.tags):
                    continue

                if len(row.sheet_name) != 1 and row.type not in [
                    "data_sheet",
                    ContentIndexType.SURVEY.value,
                ]:
                    LOGGER.critical(
                        f"For {row.type} rows, exactly one sheet_name has to be"
                        " specified"
                    )

                if row.type == "content_index":
                    sheet = self._get_sheet_or_die(row.sheet_name[0])

                    with logging_context(f"{sheet.name}"):
                        self._process_content_index_table(sheet)
                elif row.type == "data_sheet":
                    if not len(row.sheet_name) >= 1:
                        LOGGER.critical(
                            "For data_sheet rows, at least one sheet_name has to be"
                            " specified"
                        )

                    self._process_data_sheet(row)
                elif row.type == "template_definition":
                    if row.new_name:
                        LOGGER.warning(
                            "template_definition does not support 'new_name'; "
                            f"new_name '{row.new_name}' will be ignored."
                        )

                    self._add_template(row, True)
                elif row.type == "create_flow":
                    self.flow_definition_rows.append((logging_prefix, row))
                elif row.type == "create_campaign":
                    campaign_parser = self.create_campaign_parser(row)
                    name = campaign_parser.campaign.name

                    if name in self.campaign_parsers:
                        LOGGER.warning(
                            f"Duplicate campaign definition sheet '{name}'. "
                            "Overwriting previous definition."
                        )

                    self.campaign_parsers[name] = (logging_prefix, campaign_parser)
                elif row.type == "create_triggers":
                    self.trigger_parsers[row.sheet_name[0]] = (
                        logging_prefix,
                        self.create_trigger_parser(row),
                    )
                elif row.type == ContentIndexType.SURVEY.value:
                    self._add_survey(row, logging_prefix)
                elif row.type == "ignore_row":
                    self._process_ignore_row(row.sheet_name[0])
                else:
                    LOGGER.error(f"invalid type: '{row.type}'")

    def _add_template(self, row, update_duplicates=False):
        sheet_name = row.sheet_name[0]

        if sheet_name in self.template_sheets and update_duplicates:
            LOGGER.info(
                f"Duplicate template definition sheet '{sheet_name}'. "
                "Overwriting previous definition."
            )

        if sheet_name not in self.template_sheets or update_duplicates:
            sheet = self._get_sheet_or_die(sheet_name)
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

    def _get_sheet_or_die(self, sheet_name):
        candidates = self.reader.get_sheets_by_name(sheet_name)

        if not candidates:
            raise ParserError("Sheet not found", {"name": sheet_name})

        active = candidates[-1]

        if len(candidates) > 1:
            readers = [c.reader.name for c in candidates]
            LOGGER.warning(
                "Duplicate sheets found, "
                + str(
                    {
                        "name": sheet_name,
                        "readers": readers,
                        "active": active.reader.name,
                    }
                ),
            )

        return active

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
                    "Implicitly concatenating data sheets without concat operation. "
                    "Implicit concatenation is deprecated and may be removed "
                    "in the future."
                )
            data_sheet = self._data_sheets_concat(sheet_names, row.data_model)

        else:
            if not row.new_name:
                LOGGER.critical(
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
                LOGGER.critical(f'Unknown operation "{row.operation}"')

        new_name = row.new_name or sheet_names[0]

        if new_name in self.data_sheets:
            LOGGER.warn(
                f"Duplicate data sheet {new_name}. Overwriting previous definition."
            )

        self.data_sheets[new_name] = data_sheet

    def _get_data_sheet(self, sheet_name, data_model_name):
        if sheet_name in self.data_sheets:
            return self.data_sheets[sheet_name]
        else:
            return self._get_new_data_sheet(sheet_name, data_model_name)

    def _get_new_data_sheet(self, sheet_name, data_model_name=None):
        user_model = None

        if data_model_name:
            if hasattr(globalrowmodels, data_model_name):
                user_model = getattr(globalrowmodels, data_model_name)
            if self.user_models_module:
                if hasattr(self.user_models_module, data_model_name):
                    user_model = getattr(self.user_models_module, data_model_name)
            if not user_model:
                LOGGER.critical(
                    f'Undefined data_model_name "{data_model_name}" '
                    f"in {self.user_models_module}."
                )

        with logging_context(sheet_name):
            data_table = self._get_sheet_or_die(sheet_name).table

            if not user_model:
                LOGGER.info("Inferring RowModel automatically")
                user_model = model_from_headers(sheet_name, data_table.headers)

            data_rows = SheetParser(data_table, user_model).parse_all()
            model_instances = OrderedDict((row.ID, row) for row in data_rows)

            return DataSheet(model_instances, user_model)

    def _data_sheets_concat(self, sheet_names, data_model_name):
        all_data_rows = OrderedDict()
        user_model = None

        for sheet_name in sheet_names:
            with logging_context(sheet_name):
                data_sheet = self._get_data_sheet(sheet_name, data_model_name)

                if user_model and user_model is not data_sheet.row_model:
                    LOGGER.critical(
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
                LOGGER.critical(f"Invalid filtering expression: {e}")
            except SyntaxError as e:
                LOGGER.critical(
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
            LOGGER.critical(f"Invalid sorting expression: {e}")
        except SyntaxError as e:
            LOGGER.critical(
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
        sheet = self._get_sheet_or_die(sheet_name)
        rows = SheetParser(sheet.table, CampaignEventRowModel).parse_all()
        return CampaignParser(row.new_name or sheet_name, row.group, rows)

    def create_trigger_parser(self, row):
        sheet_name = row.sheet_name[0]
        sheet = self._get_sheet_or_die(sheet_name)
        rows = SheetParser(sheet.table, TriggerRowModel).parse_all()
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
