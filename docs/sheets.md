# Generic parsers from spreadsheets to data models

On an idealized and simplified level, we have the following chain of converting different representations of data:

Spreadsheet File: An XLSX, folder of CSVs, ID of a Google Sheet, flat JSON
(list of dicts mapping column headers to column entries)

^<br>
| `SheetReader`: Upon construction, reads a file and then has a dict
of `Sheet`s indexed by name.<br>
v

`Sheet`: Wrapper around [tablib.Dataset]

^<br>
| `SheetParser`, `RowParser`, `CellParser`<br>
v

`RowDataSheet`: Wrapper around `List[RowModel]` for some `RowModel`,
which is a subclass of [pydantic.BaseModel]

^<br>
| pydantic functionality<br>
v

Nested dict/JSON

`RowModel`s are classes representing the data contained in an individual row. Thus, the data in one row is a `RowModel` instance. `RowModel` may contain basic types, lists or other `pydantic.BaseModel`s as attributes, and thereby their data can be nested.

In practice, `Sheet` and `RowDataSheet` are used somewhat inconsistently, and in their stead sometimes `tablib.Dataset`, `List[RowModel]` or other custom classes are used, maybe motivating a refactor in the future. We outline the details of the three conversion steps below.


## Conversion between spreadsheet files and `Sheet`s

SheetReaders and `Sheet`s are defined in `rpft.parsers.sheets`.

The `Sheet` class wraps [tablib.Dataset] (which is often referred to as `table`). `Sheet`s also have a `name`.


### Forward direction

`Sheet`s are produced by SheetReaders that can read different input file formats. Currently, `Sheet`s have an additional SheetReader attribute `reader` indicating which reader produced it, which may be useful for error reporting.

`SheetReader`s take a file reference upon construction and provide the following method to access `Sheet`s by name:

- `get_sheet(name) -> Sheet`

The name of a sheet within a file is always unique.

We have subclasses of `AbstractSheetReader` for different formats:

- XLSX
- CSV (file reference is a folder containing CSVs)
- Google Sheet (reference is an ID)
- flat JSON (contains a dict mapping sheet names to their content. Each content is a list of dicts mapping column headers to column entries)


### Reverse direction

The are currently no SheetWriters, and thus this conversion step is one-directional. When we want to write spreadsheets, this is implemented ad-hoc by using the functionality of `tablib.Dataset` to export to CSV and XLSX. For example, see [RowDataSheet.export](/src/rpft/parsers/common/rowdatasheet.py), or `json.dump` for flat JSON.


## Conversion between `Sheet`s and `RowDataSheet`s

While `Sheet` is a simple table representation of a sheet with rows and columns (which have column headers), a [RowDataSheet](/src/rpft/parsers/common/rowdatasheet.py) represents a list of `RowModel` instances. `RowModel`s are subclasses of [pydantic.BaseModel], and may contain basic types, lists and other models as attributes, nested arbirarily deep. How sheets and their column headers correspond to `RowModel`s is documented in more detail in [models](models.md).


### Forward direction

The conversion from `Sheet` and `RowDataSheet` invokes a 3 level hierarchy:

- `SheetParser`
  - `RowParser`
    - `CellParser`


#### Sheet parser

The [SheetParser](/src/rpft/parsers/common/sheetparser.py) has a `table` (`tablib.Dataset`) and a `RowParser` and provides two functions:

- `parse_all`: returns the output as `List[RowModel]`
- `get_row_data_sheet`: returns the output as `RowDataSheet`

The `SheetParser` invokes the `RowParser` to convert each of the rows. The `RowParser` has the `RowModel` that each row is to be converted to.


#### Row parser

A [RowParser](/src/rpft/parsers/common/rowparser.py) has an associated `RowModel` and a `CellParser`.

It provides a function `parse_row(data)` to convert a spreadsheet row into a `RowModel` instance containing the provided data. `data` is a `dict[str, str]` mapping column headers to the corresponding entry of the spreadsheet in this row, and is provided by the `SheetParser`. Column headers determine which field of the model the column contains data for, and different ways to address fields in the data models are supported, see [models](models.md).

The `RowParser` interprets the column headers and if the column contains a non-basic type (e.g. a list or a submodel), it invokes the `CellParser` to convert the cell content into a nested list, which it then processes further to assign values to the model fields.


#### Cell parser

The [CellParser](/src/rpft/parsers/common/cellparser.py) has a function `parse(value)` that takes a string (the cell content) and converts it into a nested list. It uses `|` and `;` characters (in that order) as list separators. `\` can be used as an escape character.

Examples:

- `a;b` --> ['a','b']
- `a\;b` --> 'a;b'
- `a,b|1,2` --> [['a','b'],['1','2']]

More examples can be found in [/tests/test\_cellparser.py](/tests/test\_cellparser.py).


#### Templating

Cells of a sheet may contain [Jinja2](https://jinja.palletsprojects.com/en/3.1.x/) templates. For example, the content of a cell may look like:

```
Hello {{user_name}}!.
```

Given a templating context mapping variable names to values, for example:

```python
{"user_name": "Chris"}
```

The template above can be evaluated to the string `Hello Chris!`.

More examples can be found in [/tests/test\_cellparser.py](/tests/test\_cellparser.py).


##### Instantiating templated sheets

A `SheetParser` may have a templating context, that it passes down to the `RowParser` for each row, which in turn passes it down to the `CellParser` for each cell. The `CellParser` will try to evaluate all templates that appear in the cell and throw an error if a variable is undefined (because it is missing from the context).

Therefore, if a `Sheet` contains templates, we need a templating context in order to instantiate the templates and convert the `Sheet` into a `RowDataSheet`. It is not possible to convert `Sheet`s with uninstantiated templates into `RowDataSheet`s (and thus also nested JSONs).

If we want to store such sheets as JSON, we have to store it as flat JSON. In fact, such a conversion of uninstatiated templates is in principle not possible, as the following example shows. Imagine we have a column encoding a `list` field in our `RowModel`, and the corresponding cell contains:

```
{% for e in my_list %}{{e}};{% endfor %}
```

Given the context:

```python
{"my_list": [1, 2, 3]}
```

The template will be evaluated to `"1;2;3;"`, which will be interpreted by the `CellParser` as the list `[1, 2, 3]`. The `RowParser` then assigns the list to the field in the `RowModel`. However, uninstantiated, this cell contains the raw template as a string, and the `RowParser` cannot assign a string to a field of type `list`.


##### Control flow and changing context

In addition to `parse_all`, the `SheetParser` also offers a function `parse_next_row` to parse a sheet row by row. The invoker of `parse_next_row` may change the templating context between calls by using `add_to_context` and `remove_from_context`. Thus, the invoker may interpret the content of a row, and adjust the templating context accordingly before parsing the next row. The invoker may also repeat the parsing of rows by setting and returning to bookmarks, e.g. to implement for loops, using `create_bookmark`, `go_to_bookmark` and `remove_bookmark`.


### Reverse direction

The `RowDataSheet` class has a method `convert_to_tablib` which converts its content to `tablib.Dataset`. It uses the `unparse_row` method of the `RowParser` associated to the `RowDataSheet` to turn each `RowModel` instance into a `dict[str,str]` mapping column headers to a string representation of their content. In the process, it converts complex types into nested lists and uses the `CellParser`'s `join_from_lists` method to get a string representation of nested lists.

By default, the column headers are chosen in such a way that every column contains a basic type. For example, for list fields, we have one column per entry. As there are many different possible sheet representations of a `RowModel`, depending on the choice of the headers, the `RowDataSheet` has two more optional arguments:

- `target_headers` (`set[str]`): Complex type fields (`RowModel`, `list`, `dict`) whose content should be represented in the output dict as a single entry. A trailing asterisk may be used to specify multiple fields at once, such as `list.*` and `field.*`.
- `excluded_headers` (`set[str]`): Fields to exclude from the output. Same format as target_headers.

Remark: No templating is supported in the reverse direction.


## Conversion between `RowDataSheet`s and Nested JSON

As `RowModel`s are instances of `pydantic.BaseModel`, it is easy to convert them to `dict` or JSON:

Reading/writing a single `RowModel` instance from/to json:

- `RowModel.parse_json(nested_json)`
- `rowmodelinstance.json()`

In practice, we have a list of `RowModel`s, which we want to convert into a single JSON containing a list of rows (and possibly additional metadata). Thus we can use the conversion to dict functions and then process the results further, as needed:

- `RowModel.parse_obj(nested_dict)`
- `rowmodelinstance.dict()`

It would be desirable to add a method to `RowDataSheet` to export its content to a nested JSON. The reverse is less straight-forward, as we need to store some metadata describing the model somewhere - either via headers, JSON Schema, or a reference to an already defined model.

The CLI command `save_data_sheets` implements exporting all data sheets referenced in a content index as (a single) nested JSON. This is implemented in `save_data_sheets` in [/src/rpft/converters.py](/src/rpft/converters.py), using the [ContentIndexParser](rapidpro.md). However, it its own `DataSheet` class via its `to_dict` method. It would be good to unify `DataSheet` and `RowDataSheet`, and provide this as standalone functionality, once it's decided which metadata describing the underlying model needs to be stored.

Below is some (untested) code outlining roughly how this could look like:

```python
from converters import create_sheet_reader
from rpft.parsers.common.model_inference import model_from_headers
import importlib

def convert_to_nested_json(input_file, sheet_format, user_data_model_module_name=None):
    """
    Convert source spreadsheet(s) into nested json.

    :param input_file: source spreadsheet to convert
    :param sheet_format: format of the input spreadsheet
    :param user_data_model_module_name: see ContentIndexParser
    :returns: content of the input file converted to nested json.
    """

    reader = create_sheet_reader(sheet_format, input_file)
    # reader.sheets: Mapping[str, Sheet]
    # user_data_model_module_name: We need this once
    user_models_module = None
    if user_data_model_module_name:
        user_models_module = importlib.import_module(
            user_data_model_module_name
        )
    sheets = {}
    for sheet_name, sheet in reader.sheets.items():
        data_model_name = ...  # This is not stored anywhere. We need this for each sheet
    	user_model = infer_model(sheet.name, user_models_module, data_model_name, sheet.table.headers)
        rows = sheet_to_list_of_nested_dict(sheet, user_model)
        sheets[sheet_name] = rows
    return sheets

def sheet_to_list_of_nested_dict(sheet, user_model):
	'''
	The first three lines of this is a common functionality already used in various places,
	and should be wrapped in a function (and the output should probably be RowDataSheet
	rather than List[RowModel]).
	'''
    row_parser = RowParser(user_model, CellParser())
    sheet_parser = SheetParser(sheet.table, row_parser)
    data_rows = sheet_parser.parse_all()  # list of row model
    return [row.dict() for row in data_rows]
    # Below is what the content index parser does:
    # it stores it as a dict rather than list, assuming an ID column
    # model_instances = OrderedDict((row.ID, row) for row in data_rows)
    # return DataSheet(model_instances, user_model)

def nested_json_to_data_sheet(row, user_models_module=None, data_model_name=None, headers=None):
    # rows: a list of nested dicts
    user_model = infer_model("model_name?", user_models_module, data_model_name, headers)
    data_rows = []
    for row in rows:
        # Remark: there is also parse_raw for json strings and parse_file,
        # however, I assume these are not applicable here because we have some
        # meta information inside our files.
        data_rows.append(user_model.parse_obj(row))
    return data_rows
    # Alternatively, using DataSheet again:
    # model_instances = OrderedDict((row.ID, row) for row in data_rows)
    # return DataSheet(model_instances, user_model)

def infer_model(name, user_models_module=None, data_model_name=None, headers=None)
    # returns a subclass of https://docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel
    if user_models_module and data_model_name:
        user_model = getattr(user_models_module, data_model_name)
    else:
        user_model = model_from_headers(name, headers)
    return user_model
```


[tablib.Dataset]: https://tablib.readthedocs.io/en/stable/api.html#dataset-object
[pydantic.BaseModel]: https://docs.pydantic.dev/latest/concepts/models/#basic-model-usage
