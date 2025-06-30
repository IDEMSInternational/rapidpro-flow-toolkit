# RapidPro Flow Toolkit

Toolkit for using spreadsheets to create and modify RapidPro flows.

# Quickstart

```sh
pip install rpft
rpft --help
```

# Command Line Interface (CLI)

The CLI supports the following subcommands:

- `create_flows`: create RapidPro flows (in JSON format) from spreadsheets using content index
- `flows_to_sheets`: convert RapidPro flows (in JSON format) into spreadsheets
- `convert`: save input spreadsheets as JSON

Full details of the available options for each can be found via the help feature:

```sh
rpft <subcommand> --help
```

## Examples

Below is a concrete example of a valid execution of the command line tool using `create_flows` to convert a set of spreadsheets into RapidPro flows. The line breaks are merely for improving readability; the command would also be valid on a single line.

```sh
cd tests/input/example1
PYTHONPATH=. rpft create_flows \
  --output flows.json \
  --datamodels=nestedmodel \
  --format=csv \
  csv_workbook
```

The following is an example of the `flows_to_sheets` operation, essentially the reverse of `create_flows`.

```sh
mkdir output
rpft flows_to_sheets tests/output/all_test_flows.json output --strip_uuids
```

# Using the toolkit in other Python projects

1. Add the package `rpft` as a dependency of your project e.g. in requirements.txt or pyproject.toml
1. Import the `create_flows` function
1. Call `create_flows` to convert spreadsheets to flows

```python
from rpft.converters import create_flows

sources = ["workbook.xlsx", "csv_workbook"]
create_flows(
    sources, "flows.json", "csv", data_models="your_project.models"
)
```

_It should be noted that this project is still considered beta software that may change significantly at any time._

# RapidPro flow spreadsheet format

The expected contents of the input spreadsheets is documented separately:

- [RapidPro sheet specification]
- [New features documentation]

# Google Sheets integration

The toolkit can fetch spreadsheets from Google Sheets. See the [setup instructions] for details.

# Logging

To override the default logging configuration, see [Logging].

# Development

For instructions on how to set up your development environment for developing the toolkit, see the [development] page.


[development]: docs/development.md
[RapidPro sheet specification]: https://docs.google.com/document/d/1m2yrzZS8kRGihUkPW0YjMkT_Fmz_L7Gl53WjD0AJRV0/edit?usp=sharing
[New features documentation]: https://docs.google.com/document/d/1Onx2RhNoWKW9BQvFrgTc5R5hcwDy1OMsLKnNB7YxQH0/edit?usp=sharing
[setup instructions]: docs/google.md
[Logging]: docs/logging.md
