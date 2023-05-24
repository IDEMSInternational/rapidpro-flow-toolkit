import json
from rapidpro_flow_tools.parsers.creation.contentindexparser import ContentIndexParser
from rapidpro_flow_tools.parsers.sheets.csv_sheet_reader import CSVSheetReader
from rapidpro_flow_tools.parsers.sheets.xlsx_sheet_reader import XLSXSheetReader
from rapidpro_flow_tools.parsers.sheets.google_sheet_reader import GoogleSheetReader
from rapidpro_flow_tools.rapidpro.models.containers import RapidProContainer

def convert_flow(command, input_file, output_file, sheet_format, data_models=None, credentials=None, token=None):
    if command != 'create_flows':
        print(f"Command {command} currently unsupported.")
        return

    if sheet_format == 'csv':
        sheet_reader = CSVSheetReader(input_file)
    elif sheet_format == 'xlsx':
        sheet_reader = XLSXSheetReader(input_file)
    elif sheet_format == 'google_sheets':
        credentials_path = credentials or 'credentials.json'
        token_path = token or 'token.json'
        sheet_reader = GoogleSheetReader(input_file, credentials_path, token_path)
    else:
        print(f"Format {sheet_format} currently unsupported.")
        return

    ci_parser = ContentIndexParser(sheet_reader, data_models)
    output = ci_parser.parse_all_flows()
    json.dump(output.render(), open(output_file, 'w'), indent=4)
