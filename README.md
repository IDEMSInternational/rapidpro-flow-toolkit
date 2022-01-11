# RapidPro Flow Toolkit
Toolkit for using spreadsheets to create and modify RapidPro flows 

This is a clean up of https://github.com/IDEMSInternational/conversation-parser

In the future this should also include a rewrite of https://github.com/geoo89/rapidpro_abtesting

## Setup
1. Install python `>=3.6`
2. Run `pip install -r requirements.txt`

## Running Tests
1. Run `python -m unittest`


# Components

## RapidPro models

See `./rapidpro/models`. Models for flows, nodes, etc, with convenience
functions to assemble RapidPro flows. Each model has a `render` method
to render the model into a dictionary, that can be exported to a json
file whose fields are consistent with the format used by RapidPro.

## Standard format flow parser

See `./parsers/creation/standard_parser.py`. Parser to turn sheets in
the standard format (Documentation TBD) into RapidPro flows.
See `./tests/input` and `./tests/output` for some examples.

## Row parser

See `./parsers/common/row_parser.py`. Parser to turn rows of a sheet
into a specified data model. Column headers determine which field of the
model the column contains data for, and different ways to address fields
in the data models are supported. See `./parsers/common/tests/test_full_rows.py`
and `./parsers/common/tests/test_differentways.py` for examples.

## Cell parser

See `./parsers/common/cell_parser.py`. Parser to convert a spreadsheet cell
into a nested list. (Currently no nesting as only `;` is supported as an
element separator.)
