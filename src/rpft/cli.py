import argparse
import json

from rpft import converters
from rpft.logger.logger import initialize_main_logger

LOGGER = initialize_main_logger()


def main():
    args = create_parser().parse_args()
    if args.command == "create_flows":
        create_flows(args)
    if args.command == "convert_to_json":
        convert_to_json(args)


def create_flows(args):
    if len(args.output) != 1:
        print("create_flows needs exactly one output filename.")
        return

    flows = converters.create_flows(
        args.input,
        None,
        args.format,
        data_models=args.datamodels,
        tags=args.tags,
    )

    with open(args.output[0], "w") as export:
        json.dump(flows, export, indent=4)


def convert_to_json(args):
    if len(args.input) != len(args.output):
        print("convert_to_json needs exactly one output filename for each input.")
        return

    for infile, outfile in zip(args.input, args.output):
        content = converters.convert_to_json(infile, args.format)
        with open(outfile, "w") as export:
            export.write(content)


def create_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Generate RapidPro flows JSON from spreadsheets\n"
            "\n"
            "Example usage:\n"
            "create_flows --output=flows.json --format=csv --datamodels=example.models"
            " sheet1.csv sheet2.csv"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["create_flows", "convert_to_json"],
        help=(
            "create_flows: create flows from spreadsheets\n"
            "convert_to_json: dump each input spreadsheet as json\n"
            "flow_to_sheet: create spreadsheets from flows (not implemented)"
        ),
    )
    parser.add_argument(
        "input",
        nargs="+",
        help=(
            "XLSX/JSON: paths to files on local file system\n"
            "CSV: paths to csv-containing folders on local file system\n"
            "Google Sheets: sheet ID i.e."
            " https://docs.google.com/spreadsheets/d/[ID]/edit"
        ),
    )
    parser.add_argument("-o", "--output", nargs="+", help="Output JSON filename(s)")
    parser.add_argument(
        "-f",
        "--format",
        required=True,
        choices=["csv", "google_sheets", "json", "xlsx"],
        help="Input sheet format",
    )
    parser.add_argument(
        "--datamodels",
        help=(
            "Module name of the module defining user data models, i.e. models "
            "underlying the data sheets. E.g. if the model definitions reside in "
            "./myfolder/mysubfolder/mymodelsfile.py, then this argument should be "
            "myfolder.mysubfolder.mymodelsfile"
        ),
    )
    parser.add_argument(
        "--tags",
        nargs="*",
        help=(
            "Tags to filter the content index sheet. A sequence of lists, with each "
            "list starting with an integer (tag position) followed by tags to include "
            "for this position. Example: 1 foo bar 2 baz means: only include rows if "
            "tags:1 is empty, foo or bar, and tags:2 is empty or baz"
        ),
    )
    return parser


if __name__ == "__main__":
    main()
