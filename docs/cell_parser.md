# Cell Parser

Lives in rpft/parsers/common/cellparser.py, uses jinja to replace values from the row's context.

## The parser syntax

Allows access to data in a row by the headers/column IDs.

`{@value@}`

`value` can be a
- Column ID e.g. `{@name_column@}`
- A list of Column IDs e.g. `{@[name_column, age_column]@}`
- A dict of Column IDs e.g. `{@{'name': name_column,'age': age_column}@}`

The parser can also do more complex pythonic things, like `{{name_column.format(val=val)}}`, see the [Example on formatting strings](content_index.md#example:-passing-formatting-strings).

`{@value@}` returns an object, `{{value}}` always returns a string.

# Open Questions:

## Parsing debug

assign_value in rpft/parsers/common/rowparser.py#194 - should we have logging to say when something containing an `@` failed to parse to the expected? e.g. `{@colA}` parsed to unknown would be good info
