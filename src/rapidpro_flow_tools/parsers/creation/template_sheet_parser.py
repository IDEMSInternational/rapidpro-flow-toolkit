from parsers.creation.flowparser import FlowParser
from rapidpro.models.containers import RapidProContainer
from parsers.common.sheetparser import SheetParser


class TemplateSheetParser:
    # Takes a sheet defining a (templated) flow,
    # and a sheet defining instances of the template,
    # and generates one flow per instance.
    # The model representing the format of the template instance sheet
    # is implicit in the row parser

    def __init__(self, row_parser):
        self.row_parser = row_parser

    def parse_sheet(self, template_data_table, flow_definition_table):
        template_sheet_parser = SheetParser(self.row_parser, template_data_table)
        template_rows = template_sheet_parser.parse_all()
        rapidpro_container = RapidProContainer()

        for row in template_rows:
            parser = FlowParser(rapidpro_container, table=flow_definition_table, flow_name=row.ID, context=dict(row))
            parser.parse()

        return rapidpro_container
