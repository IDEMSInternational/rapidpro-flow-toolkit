# Generic parsers from spreadsheets to data models

## Cell parser

See `./parsers/common/cellparser.py`. Parser to convert a spreadsheet cell
into a nested list. (Currently no nesting as only `;` is supported as an
element separator.)

## Row parser

See `./parsers/common/rowparser.py`. Parser to turn rows of a sheet
into a specified data model. Column headers determine which field of the
model the column contains data for, and different ways to address fields
in the data models are supported. See `./parsers/common/tests/test_full_rows.py`
and `./parsers/common/tests/test_differentways.py` for examples.

The reverse operation is also supported, but only to a limited extent:
All models are spread out into a flat dict of fields, each becoming the
header of a column.

## Sheet parser

See `./parsers/common/sheetparser.py`.

# RapidPro tools

## RapidPro models

See `./rapidpro/models`. Models for flows, nodes, etc, with convenience
functions to assemble RapidPro flows. Each model has a `render` method
to render the model into a dictionary, that can be exported to a json
file whose fields are consistent with the format used by RapidPro.

## Standard format flow parser

See `./parsers/creation/flowparser.py`. Parser to turn sheets in
the standard format (Documentation TBD) into RapidPro flows.
See `./tests/input` and `./tests/output` for some examples.

Examples:
- `./tests/test_flowparser.py`
- `./parsers/creation/tests/test_flowparser.py`

## Parsing collections of flows (with templating)

See `./parsers/creation/contentindexparser.py`, `parse_all_flows`.
Examples:
- `./tests/test_contentindexparser.py`
- `./parsers/creation/tests/test_contentindexparser.py`
