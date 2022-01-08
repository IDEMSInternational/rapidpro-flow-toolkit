import json
import argparse
import logging
import csv
import os

from parsers.creation.standard_parser import Parser
from parsers.common.rowparser import RowParser
from parsers.creation.standard_models import RowData
from parsers.common.cellparser import CellParser
from rapidpro.models.containers import RapidProContainer

def get_dict_from_csv(filename):
    with open(filename, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        return [row for row in csv_reader]

def main():
    description = 'Generate RapidPro JSON from Spreadsheet.\n\n'\
                  'Example input: tests/input/master_sheet.csv\n'\
                  'Note: (Master) sheet parsing will be a separate component and'\
                  ' is only included in here as a proof of concept.'
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('input', help='Master spreadsheet listing all sheets to be processed (CSV).')
    parser.add_argument('output', help='RapidPro JSON file to write the output to.')
    parser.add_argument('--logfile', help='File to log warnings and errors to.')
    args = parser.parse_args()

    if args.logfile:
        logging.basicConfig(filename=args.logfile, level=logging.WARNING, filemode='w')

    # This functionality shouldn't be in main.py, but be done by a separate component.
    rpc = RapidProContainer()
    sheets = get_dict_from_csv(args.input)
    for sheet in sheets:
        if sheet['status'] != 'released' or sheet['flow_type'] != 'flow':
            continue
        rows = get_dict_from_csv(os.path.join(os.path.dirname(args.input), sheet['sheet_name'] + '.csv'))
        row_parser = RowParser(RowData, CellParser())
        rows = [row_parser.parse_row(row) for row in rows]
        parser = Parser(data_rows=rows, flow_name=sheet['flow_name'])
        parser.parse()
        rpc.add_flow(parser.get_flow())
    rpc.update_global_uuids()
    json.dump(rpc.render(), open(args.output, 'w'), indent=4)

if __name__ == '__main__':
    main()
