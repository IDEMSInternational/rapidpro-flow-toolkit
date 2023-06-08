import argparse

from rpft.converters import create_flows
from rpft.logger.logger import initialize_main_logger

LOGGER = initialize_main_logger()


def main():
    args = create_parser().parse_args()
    create_flows(
        args.input,
        args.output,
        args.format,
        data_models=args.datamodels,
        tags=args.tags,
    )


def create_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Generate RapidPro flows JSON from spreadsheets\n"
            "\n"
            "Example usage:\n"
            "create_flows --output=flows.json --format=csv "
            "--datamodels=example.models sheet1.csv sheet2.csv"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["create_flows"],
        help=(
            "create_flows: create flows from spreadsheets\n"
            "flow_to_sheet: create spreadsheets from flows (not implemented)"
        ),
    )
    parser.add_argument(
        "input",
        nargs="+",
        help=(
            "CSV/XLSX: path to files on local file system\n"
            "Google Sheets: sheet ID i.e. https://docs.google.com/spreadsheets/d/[ID]/edit"
        ),
    )
    parser.add_argument("-o", "--output", required=True, help="Output JSON filename")
    parser.add_argument(
        "-f",
        "--format",
        required=True,
        choices=["csv", "xlsx", "google_sheets"],
        help="Input sheet format",
    )
    parser.add_argument(
        "--datamodels",
        help=(
            "Module defining models for data sheets e.g. if the definitions reside in "
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
