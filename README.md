# RapidPro Flow Toolkit

Toolkit for using spreadsheets to create and modify RapidPro flows.

# Quickstart

```sh
pip install rpft
rpft --help
```

# Command Line Interface (CLI)

The CLI allows spreadsheets in various formats to be converted to RapidPro flows in JSON format. Full details of the available options can be found via the help feature:

```sh
rpft --help
```

Below is a concrete example of a valid execution of the command line tool. The line breaks are merely for improving readability; the command would also be valid on a single line.

```sh
rpft create_flows \
  --output flows.json \
  --datamodels=tests.input.example1.nestedmodel \
  --format=csv \
  src/rpft/tests/input/example1/content_index.csv
```

# Using the toolkit in other Python projects

1. Add the package `rpft` as a dependency of your project e.g. in requirements.txt or pyproject.toml
1. Import the `create_flows` function
1. Call `create_flows` to convert spreadsheets to flows

```python
from rpft.converters import create_flows

sheets = ["sheet1.csv", "sheet2.csv"]
create_flows(
    sheets, "flows.json", "csv", data_models="your_project.models"
)
```

_It should be noted that this project is still considered beta software that may change significantly at any time._

# RapidPro flow spreadsheet format

The expected contents of the input spreadsheets is [documented separately][3].

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
