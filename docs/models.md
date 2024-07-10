# Models

`RowModel`s are subclasses of [pydantic.BaseModel], and may contain basic types, lists and other models as attributes, nested arbirarily deep. Every `Sheet` can only be parsed in the context of a given `RowModel` (which can, however, be automatically inferred from the sheet headers, if desired).

Technically, there is no `RowModel` class, but instead is called `ParserModel` and is defined in `rpft.parsers.common.rowparser`. `ParserModel` attributes have to be basic types, lists or `ParserModel`s. The only additions to `pydantic.BaseModel` are the optional methods:

- `header_name_to_field_name`
- `field_name_to_header_name`
- `header_name_to_field_name_with_context` (for full row models)

These methods allow remapping column header names to different model attributes, for example:

```python
class SubModel(ParserModel):
    word: str = ""
    number: int = 0

class MyModel(ParserModel):
    numbers: List[int] = []
    sub: SubModel = SubModel()
```

The following table could be parsed into an instance of `MyModel`:

|numbers.1 | numbers.2 | sub.word | sub.number |
|----------|-----------|----------|------------|
| 42       | 16        | hello    |  24        |

Each column contains a basic type, in this case, `int`, `int`, `str`, `int`. However, the table could be expressed differently.

|numbers | sub                   |
|--------|-----------------------|
| 42;16  | word;hello\|number;24 |

The first column has type `List[int]`, the second `SubModel`. How sheets and their column headers correspond to `RowModel`s is specified in the [RapidPro sheet specification].

More examples can be found in the tests:

- `tests.test_rowparser`
- `tests.test_full_rows`
- `tests.test_differentways`

The method `header_name_to_field_name` and related `ParserModel` methods can be used to map column headers to fields of a different name, for example:

```python
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

Then, the following would be a valid table that can be converted into `MyModel` instances.

| number | name |
|--------|------|
| 42     | John |

The original motivation for this feature was that the original flow sheet format had a column named 'from', which is a keyword in Python, and thus could not be used as a field name, so it had to be remapped.

There is also a more complex use case where we have a list of conditions, each condition being a model with multiple attributes, such as value, variable and name (when we think of it from a OOP standpoint). However, the original sheet format had columns 'condition', 'condition\_variable', 'condition\_name', etc, containing a list of the value/variable/name fields respectively, so technically their headers should have been 'condition.\*.value', 'condition.\*.variable' and 'condition.\*.name'. The remapping feature is used to map the short forms to the accurate forms.

Then there is the context specific remapping, where remapping happens taking the content of the row into account. In practice, we remap certain headers based on a row type (encoded in a type column). This is when different row types have different attributes (so really it's arguable whether they should be in a spreadsheet at all), and for compactness, we map some of their attributes to the same column header. In particular, each row type has a 'main argument', which may be of different types, which all get mapped to the 'message_text' column header.

The module `rpft.parsers.creation.flowrowmodel` shows all of these use cases.


## Automatic model inference

Models of sheets can now be automatically inferred if no explicit model is provided, see [model inference].

This is done exclusively by parsing the header row of a sheet. Headers can be annotated as basic types and `list`. `dict` and existing models are currently not supported. If no annotation is present, the column is assumed to be a string.

Examples of what the data in a column can represent:
- `field`: no annotation; type assumed to be `str`
- `field:int`: integer
- `field:list`: list
- `field:List[int]`: list of integers
- `field.1`: first entry in a list
- `field.1:int`: first entry in list; integer
- `field.subfield`: subfield; string
- `field.subfield:int`: integer subfield
- `field.1.subfield`: list of objects with string subfield; first item of list

Intermediate models like in the last three examples are created automatically. Field name remapping cannot be done when using automated model inference. `*`-notation is also not currently supported, but could be done in principle.


[model inference]: /src/rpft/parsers/common/model_inference.py
[pydantic.BaseModel]: https://docs.pydantic.dev/latest/concepts/models/#basic-model-usage
[RapidPro sheet specification]: https://docs.google.com/document/d/1m2yrzZS8kRGihUkPW0YjMkT_Fmz_L7Gl53WjD0AJRV0/edit?usp=sharing
