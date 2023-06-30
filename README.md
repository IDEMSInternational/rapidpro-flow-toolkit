# RapidPro Flow Toolkit

Toolkit for using spreadsheets to create and modify RapidPro flows.

## Setup

1. Install Python >= 3.6
1. Create a virtual environment: `python -m venv .venv`
1. Activate venv: `source .venv/bin/activate`
1. Upgrade pip: `pip install --upgrade pip`
1. Install the project in dev mode: `pip install --editable .`

## Console tool

The command line interface (CLI) allows spreadsheets in various formats to be converted to RapidPro flows in JSON format. Full details of the available options can be found via the help feature:

```
python -m rapidpro_flow_tools.cli --help
```

As a quick example, try running the following command. The line breaks are merely for improving readability; the command would also be valid on a single line.

```
python -m rapidpro_flow_tools.cli create_flows \
  --output flows.json \
  --datamodels=tests.input.example1.nestedmodel \
  --format=csv \
  src/rapidpro_flow_tools/tests/input/example1/content_index.csv
```

## Processing Google Sheets

Follow the steps _Enable the API_ and _Authorize credentials for a desktop application_ from
https://developers.google.com/sheets/api/quickstart/python

Note: Google sheets need to be in native Google sheets format,
not `XLSX`, `XLS`, `ODS`, etc

## Using the toolkit in other Python projects

1. Add the package `rapidpro_flow_tools` as a dependency of your project e.g. in requirements.txt
1. Import the `create_flows` function
1. Call `create_flows` to convert spreadsheets to flows

```
from rapidpro_flow_tools.converters import create_flows

sheets = ["sheet1.csv", "sheet2.csv"]
create_flows(
    sheets, "flows.json", "csv", data_models="your_project.models"
)
```

## Running tests

```
python -m unittest discover -s src
```

# Components

## Generic parsers from spreadsheets to data models

### Cell parser

See `./parsers/common/cellparser.py`. Parser to convert a spreadsheet cell
into a nested list. (Currently no nesting as only `;` is supported as an
element separator.)

### Row parser

See `./parsers/common/rowparser.py`. Parser to turn rows of a sheet
into a specified data model. Column headers determine which field of the
model the column contains data for, and different ways to address fields
in the data models are supported. See `./parsers/common/tests/test_full_rows.py`
and `./parsers/common/tests/test_differentways.py` for examples.

The reverse operation is also supported, but only to a limited extent:
All models are spread out into a flat dict of fields, each becoming the
header of a column.

### Sheet parser

See `./parsers/common/sheetparser.py`.

## RapidPro tools

### RapidPro models

See `./rapidpro/models`. Models for flows, nodes, etc, with convenience
functions to assemble RapidPro flows. Each model has a `render` method
to render the model into a dictionary, that can be exported to a json
file whose fields are consistent with the format used by RapidPro.

### Standard format flow parser

See `./parsers/creation/flowparser.py`. Parser to turn sheets in
the standard format (Documentation TBD) into RapidPro flows.
See `./tests/input` and `./tests/output` for some examples.

Examples:
- `./tests/test_flowparser.py`
- `./parsers/creation/tests/test_flowparser.py`

### Parsing collections of flows (with templating)

See `./parsers/creation/contentindexparser.py`, `parse_all_flows`.
Examples:
- `./tests/test_contentindexparser.py`
- `./parsers/creation/tests/test_contentindexparser.py`

Documentation (request access): https://docs.google.com/document/d/1Onx2RhNoWKW9BQvFrgTc5R5hcwDy1OMsLKnNB7YxQH0/edit?pli=1#
