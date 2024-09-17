# Spreadsheet notation

Summary of spreadsheet notation used to convert sheets into a nested data structure (JSON). A series of data tables will be shown alongside the resultant JSON structure.

# Books

A container for multiple tables. Also known as a spreadsheet or workbook. A book is converted to an object containing a property for each table. The property key is the name of the sheet; the value is the converted contents of the sheet.

For example, given an Excel workbook with two sheets ("table1" and "table2"), the resulting JSON will be:

```json
{
  "table1": [],
  "table2": []
}
```

# Tables

Also known as a sheet in a spreadsheet (or workbook).

The contents of a table are converted to a sequence of objects - corresponding to rows in the sheet. Each object will have keys corresponding to the column headers of the sheet, and values corresponding to a particular row in the sheet.

| a  | b  |
|----|----|
| v1 | v2 |

`data`

```json
{
  "data": [
    {"a": "v1", "b": "v2"}
  ]
}
```

This means that the first row of every table should be a header row that specifies the name of each column.

# Basic types

Refers to the following value types in JSON: `string`, `number`, `true` and `false`.

| string | number | true | false |
|--------|--------|------|-------|
| hello  | 123    | true | false |

`basic_types`

```json
{
  "basic_types": [
    {
      "string": "hello",
      "number": 123,
      "true": true,
      "false": false
    }
  ]
}
```

The JSON type `null` is not represented because an empty cell is assumed to be equivalent to the empty string ("").

# Sequences

An ordered sequence of items. Also known as lists or arrays.

| seq1 | seq1 | seq2.1 | seq2.2 | seq3     | seq4               |
|------|------|--------|--------|----------|--------------------|
| v1   | v2   | v1     | v2     | v1 \| v2 | v1 ; v2 \| v3 ; v4 |

`sequences`

```json
{
  "sequences": [
    {
      "seq1": ["v1", "v2"],
      "seq2": ["v1", "v2"],
      "seq3": ["v1", "v2"]
      "seq4": [["v1", "v2"], ["v3", "v4"]]
    }
  ]
}
```

`seq1`, `seq2` and `seq3` are equivalent. In all cases, the order of items is specified from left to right.

`seq1` uses a 'wide' layout, where the column header is repeated and each column holds one item in the sequence. Values from columns with the same name are collected into a sequence in the resulting JSON object.

`seq2` is similar to `seq1`, but the index of each item is specified explicitly.

`seq3` uses an 'inline' layout, where the sequence is defined as a delimited string within a single cell of the table. The default delimiter is a vertical bar or pipe character ('|').

Two levels of nesting are possible within a cell, as shown by `seq4` - a list of lists. This could be used to model a list of key-value pairs, which could easily be converted to an object (map / dictionary). The default delimiter for second-level sequences is a semi-colon (';').

The interpretation of delimiter characters can be skipped by escaping the delimiter characters. An escape sequence begins with a backslash ('\\') and ends with the character to be escaped. For example, to escape a vertical bar, use: '\\|'.

# Objects

An unordered collection of key-value pairs (properties). Also known as maps, dictionaries or associative arrays.

| obj1.key1 | obj1.key2 | obj2                   |
|-----------|-----------|------------------------|
| v1        | v2        | key1 ; v1 \| key2 ; v2 |

`objects`

```json
{
  "objects": [
    {
      "obj1": {
        "key1": "v1",
        "key2": "v2"
      },
      "obj2": [
        ["key1", "v1"],
        ["key2", "v2"]
      ]
    }
  ]
}
```

`obj1` and `obj2` are slightly different, but can be interpreted in the same way, as a list of key-value pairs.

A wide layout is used for `obj1`, where one or more column headers use a dotted 'keypath' notation to identify a particular property key belonging to a particular object, and the corresponding cells in subsequent rows contain the values for that property. The dotted keypath notation can be used to access properties at deeper levels of nesting e.g. `obj.key.subkey.etc`.

An inline layout is used for `obj2`, where properties are defined as a sequence of key-value pairs. The delimiter of properties is a vertical bar or pipe character - same as top-level sequences. The delimiter of keys and values is a semi-colon character - same as second-level sequences.

All the previous notation can be combined to create fairly complicated structures.

| obj1.key1              | obj1.key1                      |
|------------------------|--------------------------------|
| 1 ; 2 ; 3 \| one ; two | active ; true \| debug ; false |

`nesting`

```json
{
  "nesting": [
    {
      "obj1": {
        "key1": [
          [
            [1, 2, 3],
            ["one", "two"]
          ],
          [
            ["active", true],
            ["debug", false]
          ]
        ],
      }
    }
  ]
}
```

# Templates

Table cells may contain Jinja templates. A cell is considered a template if it contains template placeholders anywhere within it. There are three types of template placeholders:

- `{{ ... }}`
- `{% ... %}`
- `{@ ... @}`

When converting between spreadsheets and JSON, templates will not be interpreted in any way, just copied verbatim. This means that sequence delimiters do not need to be escaped if they exist within a template. It is intended for templates to eventually be interpreted at a later stage, during further processing.

# Metadata

Information that would otherwise be lost during the conversion from spreadsheets to JSON is stored as metadata - in a top-level property with key `_idems`. The metadata property is intended to be 'hidden' and unlikely to be shared by any sheet name.

The original header names for each sheet are held as metadata to direct the conversion process from JSON back to spreadsheet. The original headers preserve the order of columns and whether a wide or inline layout was used.


| seq1 | seq1 | seq2     |
|------|------|----------|
| v1   | v2   | v1 \| v2 |

`sequences`

```json
{
  "_idems": {
    "tabulate": {
      "sequences": {
        "headers": [
          "seq1",
          "seq1",
          "seq2"
        ]
      }
    }
  }
  "sequences": [
    {
      "seq1": ["v1", "v2"],
      "seq2": ["v1", "v2"]
    }
  ]
}
```
