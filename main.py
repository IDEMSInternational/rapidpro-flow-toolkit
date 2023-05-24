import json
import argparse
import os

from parsers.creation.contentindexparser import ContentIndexParser
from parsers.sheets.csv_sheet_reader import CSVSheetReader
from parsers.sheets.xlsx_sheet_reader import XLSXSheetReader
from parsers.sheets.google_sheet_reader import GoogleSheetReader
from rapidpro.models.containers import RapidProContainer
from logger.logger import initialize_main_logger

LOGGER = initialize_main_logger()

def main():
    description = 'Generate RapidPro JSON from Spreadsheet(s).\n\n'\
                  'Example usage: \n'\
                  'create_flows tests/input/example1/content_index.csv out.json --format=csv --datamodels=tests.input.example1.nestedmodel'
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('command',
                        choices=["create_flows", "flow_to_sheet"],
                        help='create_flows: Create flows as defined in the input content index sheet.\n'\
                             '    input: Content index sheet defining flows to be created.\n'\
                             '    output: RapidPro JSON file for writing output flows.\n'\
                             'flow_to_sheet: Convert input file into a set of sheets encoding the flows.\n'
                             '    input: RapidPro JSON file to read the flows from.\n'\
                             '    output: File to write the output sheets to.\n')
    parser.add_argument('input', help='Filename, or sheet_id for google sheets (https://docs.google.com/spreadsheets/d/[spreadsheet_id]/edit)')
    parser.add_argument('output', help='Filename')
    parser.add_argument('--format', required=True, choices=["csv", "xlsx", "google_sheets"], help='Sheet format for reading/writing.')
    parser.add_argument('--datamodels', help='Module defining models for data sheets. E.g. if the definitions reside in ./myfolder/mysubfolder/mymodelsfile.py, then this argument should be myfolder.mysubfolder.mymodelsfile')
    parser.add_argument('--credentials', help='Path to the credentials.json file')
    parser.add_argument('--token', help='Path to the token.json file')
    args = parser.parse_args()

    if args.command != 'create_flows':
        print(f"Command {args.command} currently unsupported.")
        return

    if args.format == 'csv':
        sheet_reader = CSVSheetReader(args.input)
    elif args.format == 'xlsx':
        sheet_reader = XLSXSheetReader(args.input)
    elif args.format == 'google_sheets':
        credentials_path = args.credentials or 'credentials.json'
        token_path = args.token or 'token.json'
        sheet_reader = GoogleSheetReader(args.input, credentials_path, token_path)
    else:
        print(f"Format {args.format} currently unsupported.")
        return

    ci_parser = ContentIndexParser(sheet_reader, args.datamodels)
    output = ci_parser.parse_all_flows()
    json.dump(output.render(), open(args.output, 'w'), indent=4)


if __name__ == '__main__':
    main()
