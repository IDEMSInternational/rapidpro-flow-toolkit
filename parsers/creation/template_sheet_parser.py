from parsers.creation.standard_parser import Parser
from rapidpro.models.containers import RapidProContainer


class TemplateSheetParser:
    # Takes a sheet defining a (templated) flow,
    # and a sheet defining instances of the template,
    # and generates one flow per instance.
    # The model representing the format of the template instance sheet
    # is implicit in the row parser

    def __init__(self, row_parser):
        self.row_parser = row_parser

    def parse_sheet(self, template_rows, flow_rows):
        template_rows = [self.row_parser.parse_row(row) for row in template_rows]
        rapidpro_container = RapidProContainer()

        for row in template_rows:
            parser = Parser(rapidpro_container, rows=flow_rows, flow_name=row.ID, context=dict(row))
            parser.parse()

        return rapidpro_container
