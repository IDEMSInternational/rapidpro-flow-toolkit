# RapidPro tools

## ContentIndexParser

Used for parsing collections of flows (with templating). Flow-specific features are ommitted here. We only give the general idea of a content index and its parser.


The class `rpft.parsers.creation.contentindexparser.ContentIndexParser` takes a [SheetReader](sheets.md) and looks for one or multiple sheets called `content_index` and processes them (in the order provided). Rows of a content index generally reference other sheets with additional meta information. These may also be, again, content index sheets, which in that case are parsed recursively (and from a parsing order perspective, its rows are parsed right in between the rows above and the rows below of the containing content index).

In essence, for each type of sheet, the content index maintains dictionaries (one per sheet type) mapping sheet names to the actual sheets. When a content index sheet is processed, each row is inspected and the referenced sheet added to the relevant (type-specific) dictionary. If an entry with a given name already exists, it is overwritten. Thus it is possible to have a parent content index containing some data, and a (later) child content index replacing some of that data. There is also an `ignore_row` type indicating that a previously referenced sheet should be deleted from its respective index.

Sheets can also be renamed before being added to the respective dict using the `new_name` column.

Details of the content index sheet format are detailed in [New features documentation].

There are two sheet types of particular interest.

- `rpft.parsers.creation.contentindexparser.DataSheet`: Similar to a [RowDataSheet](sheets.md), but assumes that the `RowModel` has an `ID` field, and, rather than storing a list of rows, stores an ordered `dict` of rows, indexed by their ID.
- `rpft.parsers.creation.contentindexparser.TemplateSheet`: Wrapper around `tablib.Dataset`, with template arguments.

Note: It may be worthwhile unifying the data structures used here, to be consistent with `Sheet` and `RowDataSheet` documented in [sheets](sheets.md). Also see the discussion there why `DataSheet`s can be exported to nested JSON, while `TemplateSheet`s can only be exported to flat JSON.

`DataSheet`s are often used to instantiate `TemplateSheet`s, and the `ContentIndexParser` has mechanisms for this, see [New features documentation]. Furthermore, `DataSheet`s can also be concatenated, filtered and sorted via the `operation` column, see [Data sheet operations].

Relevant code in `rpft.parsers.creation.contentindexparser.ContentIndexParser.parse_all_flows`.

Examples:

- `/src/tests/test_contentindexparser.py`
- `/src/rpft/parsers/creation/tests/test_contentindexparser.py`


## FlowParser

See `rpft.parsers.creation.flowparser` and [RapidPro sheet specification]. Parser to turn sheets in the standard format (Documentation TBD) into RapidPro flows. See `/src/tests/input` and `/src/tests/output` for some examples.

Examples:

- `/src/tests/test_flowparser.py`
- `/src/rpft/parsers/creation/tests/test_flowparser.py`


## RapidPro models

See `rpft.rapidpro.models`. Models for flows, nodes, etc, with convenience functions to assemble RapidPro flows. Each model has a `render` method to render the model into a dictionary, that can be exported to a json file whose fields are consistent with the format used by RapidPro.


[Data sheet operations]: https://docs.google.com/document/d/1Onx2RhNoWKW9BQvFrgTc5R5hcwDy1OMsLKnNB7YxQH0/edit#heading=h.c93jouk7sqq
[RapidPro sheet specification]: https://docs.google.com/document/d/1m2yrzZS8kRGihUkPW0YjMkT_Fmz_L7Gl53WjD0AJRV0/edit?usp=sharing
[New features documentation]: https://docs.google.com/document/d/1Onx2RhNoWKW9BQvFrgTc5R5hcwDy1OMsLKnNB7YxQH0/edit?usp=sharing
