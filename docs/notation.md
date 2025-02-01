# Spreadsheet notation

Summary of spreadsheet notation used to convert sheets into a nested data structure (JSON). A series of data tables will be shown alongside the resultant JSON structure.

# Tables

Also known as a sheet in a spreadsheet (or workbook).

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

Additional tables (sheets) will be added as additional properties.

```json
{
  "sheet1": [{}, {}],
  "sheet2": [{}, {}]
}
```

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

`seq3` uses an 'inline' layout, where the sequence is defined as a delimited string within a single cell of the table. The default delimiter is a vertical bar or pipe character ('|').

Two levels of nesting are possible within a cell, as shown by `seq4` - a list of lists. This could be used to model a list of key-value pairs, which could easily be converted to an object (map / dictionary).

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

`obj1` and `obj2` are not quite the same, but can be interpreted in the same way, as a list of key-value pairs.

A wide layout is used for `obj1`, where one or more column headers use a dotted 'keypath' notation to identify a particular property key belonging to a particular object, and the corresponding cells in subsequent rows contain the values for that property. The dotted keypath notation can be used to access properties at deeper levels of nesting e.g. `obj.key.subkey.etc`.

An inline layout is used for `obj2`, where properties are defined as a sequence of key-value pairs. The delimiter of properties is a vertical bar or pip character - the same as for top-level arrays. The delimiter of keys and values is a semi-colon character - the same as for 2nd-level arrays.

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
