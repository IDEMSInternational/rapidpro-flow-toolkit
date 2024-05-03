# RapidPro Flow Toolkit

Toolkit for using spreadsheets to create and modify RapidPro flows.

# Quickstart

```sh
pip install rpft
rpft --help
```

# Command Line Interface (CLI)

The CLI supports three subcommands:

- `create_flows`: create RapidPro flows (in JSON format) from spreadsheets
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

# Processing Google Sheets

It is possible to read in spreadsheets via the Google Sheets API by specifying `--format=google_sheets` on the command line. Spreadsheets must be in the Google Sheets format rather than XLSX, CSV, etc.

Instead of specifying paths to individual spreadsheets on your local filesystem, you must supply the IDs of the Sheets you want to process. The ID can be extracted from the URL of the Sheet i.e. docs.google.com/spreadsheets/d/**ID**/edit.

The toolkit will need to authenticate with the Google Sheets API and be authorized to access your spreadsheets. Two methods for doing this are supported.

- **OAuth 2.0 for installed applications**: for cases where human interaction is possible e.g. when using the CLI
- **Service accounts**: for cases where interaction is not possible or desired e.g. in automated pipelines

## Installed applications

Follow the steps in the [setup your environment section][1] of the Google Sheets quickstart for Python.

Once you have a `credentials.json` file in your current working directory, the toolkit will automatically use it to authenticate whenever you use the toolkit. The refresh token (`token.json`) will be saved automatically in the current working directory so that it is not necessary to go through the full authentication process every time.

## Service accounts

Follow the steps in the [creating a service account section][2] to obtain a service account key. The toolkit will accept the key as an environment variable called `CREDENTIALS`.

```sh
export CREDENTIALS=$(cat service-account-key.json)
rpft ...
```

# Development

For instructions on how to set up your development environment for developing the toolkit, see the [development][4] page.

[1]: https://developers.google.com/sheets/api/quickstart/python#set_up_your_environment
[2]: https://developers.google.com/identity/protocols/oauth2/service-account#creatinganaccount
[3]: https://docs.google.com/document/d/1Onx2RhNoWKW9BQvFrgTc5R5hcwDy1OMsLKnNB7YxQH0/edit?pli=1#
[4]: https://github.com/IDEMSInternational/rapidpro-flow-toolkit/blob/main/docs/development.md
[RapidPro sheet specification]: https://docs.google.com/document/d/1m2yrzZS8kRGihUkPW0YjMkT_Fmz_L7Gl53WjD0AJRV0/edit?usp=sharing
[New features documentation]: https://docs.google.com/document/d/1Onx2RhNoWKW9BQvFrgTc5R5hcwDy1OMsLKnNB7YxQH0/edit?usp=sharing
