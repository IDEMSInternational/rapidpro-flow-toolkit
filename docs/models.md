# Models

`RowModel`s are subclasses of [`pydantic.BaseModel`]
(https://docs.pydantic.dev/latest/concepts/models/#basic-model-usage), and may
contain basic types, lists and other models as attributes, nested arbirarily
deep. Every `Sheet` can only be parsed in the context of a given `RowModel`
(which can, however, be automatically inferred from the sheet headers, if desired).

Technically, there is no `RowModel` class, but instead it is called `ParserModel`
and is defined in [](/src/rpft/parsers/common/rowparser.py). `ParserModel` attributes have to be
basic types, lists or `ParserModel`s.
The only addition to `pydantic.BaseModel` are the (optional) methods `header_name_to_field_name`, `field_name_to_header_name` and (for full row models) `header_name_to_field_name_with_context` that allow remapping
column header names to different model attributes. 

Example:

```
class SubModel(ParserModel):
    word: str = ""
    number: int = 0

class MyModel(ParserModel):
    numbers: List[int] = []
    sub: SubModel = SubModel()
```

The headers of a sheet and its content that can be parsed into `MyModel` could for example be:

|numbers.1 | numbers.2 | sub.word | sub.number |
|----------|-----------|----------|------------|
| 42       | 16        | hello    |  24        |

with each column containing a basic type (int, int, int, str, int).


However, the headers and content could also look like this:

|numbers | sub                   |
|--------|-----------------------|
| 42;16  | word;hello\|number;24 |

With the first column representing a `List[int]` and the second a `SubModel`.

How sheets and their column headers correspond to `RowModel`s is specified in
[RapidPro sheet specification].

More examples can also be found in the tests:

- [](/src/rpft/parsers/common/tests/test_rowparser.py)
- [](/src/rpft/parsers/common/tests/test_full_rows.py)
- [](/src/rpft/parsers/common/tests/test_differentways.py)


The `header_name_to_field_name` and related `ParserModel` methods can be used to map column headers to fields of a different name, for example:

```
class MyModel(ParserModel):
    number: int = 0
    first_name_and_surname: str = ""

    def header_name_to_field_name(header):
        if header == "name":
        	return "first_name_and_surname"
        return header

    def field_name_to_header_name(field):
        if field == "first_name_and_surname":
        	return "name"
        return field
```

Then

| number | name |
|--------|------|
| 42     | John |

would be a valid table that can be converted into `MyModel` instances.


## Automatic model inference

Models of sheets can now be automatically inferred if no explicit model is provided, see [model inference](/src/rpft/parsers/common/model_inference.py)

This is done exclusively by parsing the header row of a sheet. Headers can be annotated with types (basic types and list; dict and existing models are currently not supported). If no annotation is present, the column is assumed to be a string.

Examples of what the data in a column can represent:
- `field`: `field` is inferred to be a string
- `field:int`: `field` is inferred to be a int
- `field:list`: `field` is inferred to be a list
- `field:List[int]`: `field` is inferred to be a list of integers
- `field.1`: `field` is inferred to be a list, and this column contains its first entry
- `field.1:int`: `field` is inferred to be a list of integers, and this column contains its first entry
- `field.subfield`: `field` is inferred to be another model with one or multiple subfields, and this column contains values for the `subfield` subfield
- `field.subfield:int`: `field` is inferred to be another model with one or multiple subfields, and this column contains values for the `subfield` subfield which is inferred to be an integer
- `field.1.subfield`: `field` is inferred to be a list of another model with one or multiple subfields, and this column contains values for the `subfield` subfield of the first list entry

Intermediate models like in the last three examples are created automatically.

Field name remapping cannot be done when using automated model inference.

`*`-notation is also not currently supported, but could be done in principle.

[RapidPro sheet specification]: https://docs.google.com/document/d/1m2yrzZS8kRGihUkPW0YjMkT_Fmz_L7Gl53WjD0AJRV0/edit?usp=sharing
