import json
import argparse

from parsers.creation.contentindexparser import ContentIndexParser
from parsers.sheets.csv_sheet_reader import CSVSheetReader
from rapidpro.models.containers import RapidProContainer


def main():
    description = 'Generate RapidPro JSON from Spreadsheet(s).\n\n'\
                  'Example usage: \n'\
                  'create_flows tests/input/example1/content_index.csv out.json --format=csv --datamodels=tests.input.example1.nestedmodel'
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('command', choices=["create_flows", "flow_to_sheet"], help='What to do.')
    parser.add_argument('input', help='Content index sheet defining flows to be created.')
    parser.add_argument('output', help='RapidPro JSON file to write the output to.')
    parser.add_argument('--format', required=True, choices=["csv", "xlsx", "googlesheet"], help='Format of the content index sheet.')
    parser.add_argument('--datamodels', help='Module defining models for data sheets. E.g. if the definitions reside in ./myfolder/mysubfolder/mymodelsfile.py, then this argument should be myfolder.mysubfolder.mymodelsfile')
    args = parser.parse_args()

    if args.command != 'create_flows':
        print(f"Command {args.command} currently unsupported.")
        return

    if args.format == 'csv':
        sheet_reader = CSVSheetReader(args.input)
    else:
        print(f"Format {args.format} currently unsupported.")
        return

    ci_parser = ContentIndexParser(sheet_reader, args.datamodels)
    output = ci_parser.parse_all_flows()
    json.dump(output.render(), open(args.output, 'w'), indent=4)
    

if __name__ == '__main__':
    main()
