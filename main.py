import json
import os
import argparse

from parsers.creation.contentindexparser import ContentIndexParser
from parsers.sheets.csv_sheet_reader import CSVSheetReader
from parsers.sheets.xlsx_sheet_reader import XLSXSheetReader
from parsers.sheets.google_sheet_reader import GoogleSheetReader

from parsers.common.rowdatasheet import RowDataSheet
from rapidpro.models.containers import RapidProContainer
from parsers.common.cellparser import CellParser
from parsers.common.rowparser import RowParser
from parsers.creation.flowrowmodel import FlowRowModel

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
    parser.add_argument('output', help='Filename, or folder name (for csv)')
    parser.add_argument('--format', required=True, choices=["csv", "xlsx", "google_sheets"], help='Sheet format for reading/writing.')
    parser.add_argument('--datamodels', help='Module defining models for data sheets. E.g. if the definitions reside in ./myfolder/mysubfolder/mymodelsfile.py, then this argument should be myfolder.mysubfolder.mymodelsfile')
    args = parser.parse_args()

    if args.command == 'flow_to_sheet':
        if args.format != 'csv':
            print(f"Format {args.format} currently unsupported.")
            return

        with open(args.input, 'r') as f:
            data = json.load(f)
        container = RapidProContainer.from_dict(data)
        for flow in container.flows:
            rows = flow.to_rows()
            rds = RowDataSheet(RowParser(FlowRowModel, CellParser()), rows)
            rds.export(os.path.join(args.output, f"{flow.name}.csv"))

    elif args.command == 'create_flows':
        if args.format == 'csv':
            sheet_reader = CSVSheetReader(args.input)
        elif args.format == 'xlsx':
            sheet_reader = XLSXSheetReader(args.input)
        elif args.format == 'google_sheets':
            sheet_reader = GoogleSheetReader(args.input)
        else:
            print(f"Format {args.format} currently unsupported.")
            return

        ci_parser = ContentIndexParser(sheet_reader, args.datamodels)
        output = ci_parser.parse_all_flows()
        json.dump(output.render(), open(args.output, 'w'), indent=4)

    else:
        print(f"Command {args.command} currently unsupported.")
    

if __name__ == '__main__':
    main()
