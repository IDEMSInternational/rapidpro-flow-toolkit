import argparse
import json

from rpft import converters
from rpft.logger.logger import initialize_main_logger


def main():
    initialize_main_logger()
    args = create_parser().parse_args()
    args.func(args)


def create_flows(args):
    flows = converters.create_flows(
        args.input,
        None,
        args.format,
        data_models=args.datamodels,
        tags=args.tags,
    )

    with open(args.output, "w", encoding="utf-8") as export:
        json.dump(flows, export, indent=4)


def convert_to_json(args):
    content = converters.convert_to_json(args.input, args.format)

    with open(args.output, "wb") as export:
        export.write(bytes(content, "utf-8"))


def flows_to_sheets(args):
    converters.flows_to_sheets(
        args.input, args.output, args.format, args.strip_uuids, args.numbered
    )


def uni_to_sheets(args):
    with open(args.output, "wb") as handle:
        handle.write(converters.uni_to_sheets(args.input))


def sheets_to_uni(args):
    data = converters.sheets_to_uni(args.input)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def create_parser():
    parser = argparse.ArgumentParser(
        description=("create RapidPro flows JSON from spreadsheets"),
    )
    sub = parser.add_subparsers(
        help="run {subcommand} --help for further information",
        required=True,
        title="subcommands",
    )

    _add_create_command(sub)
    _add_convert_command(sub)
    _add_flows_to_sheets_command(sub)
    _add_uni_to_sheets_command(sub)
    _add_sheets_to_uni_command(sub)

    return parser


def _add_create_command(sub):
    parser = sub.add_parser(
        "create",
        aliases=["create_flows"],
        help="create RapidPro flows from spreadsheets",
    )

    parser.set_defaults(func=create_flows)
    parser.add_argument(
        "input",
        help=(
            "paths to XLSX or JSON files, or directories containing CSV files, or"
            " Google Sheets IDs i.e. from the URL; inputs should be of the same format"
        ),
        nargs="+",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output JSON filename",
        required=True,
    )
    parser.add_argument(
        "--tags",
        help=(
            "tags to filter the content index sheet; a sequence of lists, with each"
            " list starting with an integer (tag position) followed by tags to include"
            " or exclude for this position; exclusions are preceded by '!'; for"
            " example, the value '1 foo bar ! 2 !baz' includes rows where tags.1"
            " is 'foo', 'bar' or not empty, and tags:2 is not 'baz' or empty"
        ),
        nargs="*",
    )
    parser.add_argument(
        "--datamodels",
        help=(
            "name of the module defining user data models underlying the data sheets,"
            " e.g. if the model definitions reside in"
            " ./myfolder/mysubfolder/mymodelsfile.py, then this argument should be"
            " myfolder.mysubfolder.mymodelsfile"
        ),
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "google_sheets", "json", "uni", "xlsx"],
        help="input sheet format",
        required=True,
    )


def _add_convert_command(sub):
    parser = sub.add_parser("convert", help="save input spreadsheets as JSON")

    parser.set_defaults(func=convert_to_json)
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "google_sheets", "json", "xlsx"],
        help="input sheet format",
        required=True,
    )
    parser.add_argument(
        "input",
        help=(
            "path to XLSX or JSON file, or directory containing CSV files, or Google"
            " Sheets ID i.e. from the URL"
        ),
    )
    parser.add_argument(
        "output",
        help=("path to output JSON file"),
    )


def _add_flows_to_sheets_command(sub):
    parser = sub.add_parser(
        "flows_to_sheets", help="convert RapidPro JSON into spreadsheets"
    )

    parser.set_defaults(func=flows_to_sheets)
    parser.add_argument(
        "--strip_uuids",
        action="store_true",
        help="strip all UUIDs from output to allow for comparing outputs",
    )
    parser.add_argument(
        "--numbered",
        action="store_true",
        help="Use sequential numbers instead of short representations for row IDs",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "xlsx"],
        help="desired sheet format (default: csv)",
        default="csv",
    )
    parser.add_argument(
        "input",
        help=("path to input RapidPro JSON file"),
    )
    parser.add_argument(
        "output",
        help=("output folder"),
    )


def _add_uni_to_sheets_command(sub):
    parser = sub.add_parser(
        "uni-to-sheets",
        help="convert JSON to sheets",
    )
    parser.set_defaults(func=uni_to_sheets)
    parser.add_argument(
        "input",
        help=("location of input JSON file"),
    )
    parser.add_argument(
        "output",
        help=("location where sheets will be saved"),
    )


def _add_sheets_to_uni_command(sub):
    parser = sub.add_parser(
        "sheets-to-uni",
        help="convert sheets to nested JSON",
    )

    parser.set_defaults(func=sheets_to_uni)
    parser.add_argument(
        "input",
        help=("location of workbook"),
    )
    parser.add_argument(
        "output",
        help=("location where JSON will be saved"),
    )


if __name__ == "__main__":
    main()
