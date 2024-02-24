import argparse
import json

from rpft.converters import create_flows, save_data_sheets
from rpft.logger.logger import initialize_main_logger

LOGGER = initialize_main_logger()


def main():
    args = create_parser().parse_args()
    if args.command == "create_flows":
        output = create_flows(
            args.input,
            None,
            args.format,
            data_models=args.datamodels,
            tags=args.tags,
        )
    elif args.command == "save_data_sheets":
        output = save_data_sheets(
            args.input,
            None,
            args.format,
            data_models=args.datamodels,
            tags=args.tags,
        )
    else:
        print("Invalid command.")
        exit(0)

    with open(args.output, "w") as export:
        json.dump(output, export, indent=4)


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
        choices=["create_flows", "save_data_sheets"],
        help=(
            "create_flows: create flows from spreadsheets\n"
            "save_data_sheets: save data from spreadsheets as json\n"
            "flow_to_sheet: create spreadsheets from flows (not implemented)"
        ),
    )
    parser.add_argument(
        "input",
        nargs="+",
        help=(
            "CSV/XLSX: path to files on local file system\n"
            "Google Sheets: sheet ID i.e."
            " https://docs.google.com/spreadsheets/d/[ID]/edit"
        ),
    )
    parser.add_argument("-o", "--output", required=True, help="Output JSON filename")
    parser.add_argument(
        "-f",
        "--format",
        required=True,
        choices=["csv", "google_sheets", "xlsx"],
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
