import re
from collections import defaultdict
from collections.abc import Iterable, Sequence

from typing import List

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from rpft.parsers.common.cellparser import CellParser


def is_pairs(value):
    return all(
        isinstance(item, Sequence) and not isinstance(item, str) and len(item) == 2
        for item in value
    )


class RowParserError(Exception):
    pass


class ParserModel(BaseModel):

    model_config = ConfigDict(coerce_numbers_to_str=True)

    def header_name_to_field_name(header):
        # Given a human-friendly column header name, map it to the
        # string defining which field(s) in the model the cell
        # value corresponds to.
        # This is necessary as we might want
        # to use some string representations as fields which are
        # reserved words in python.
        return header

    def field_name_to_header_name(field):
        # Reverse of the above.
        # Currently, however, this is more limited, as field
        # only refers to top-level field entries, rather than
        # full hierarchies pointing to a field.
        return field

    def header_name_to_field_name_with_context(header, row):
        # This is used for models representing a full sheet row.
        return header

    @field_validator("*", mode="before")
    @classmethod
    def collect(cls, v, info):
        """
        Collect a single value into a list if the target field is a list
        """
        field = cls.model_fields[info.field_name]

        if is_list_type(field.annotation) and (
            not isinstance(v, Sequence) or isinstance(v, str)
        ):
            return [v] if v != "" else []

        return v

    @model_validator(mode="before")
    @classmethod
    def coerce_to_dict(cls, data):
        """
        Coerce different types of data into a dict, if possible.
        """
        if isinstance(data, str):
            data = [data]

        if isinstance(data, Sequence):
            if is_pairs(data):
                return dict(data)
            else:
                return {
                    name: val[1] if isinstance(val, list) and len(val) > 1 else val
                    for (name, _), val in zip(cls.model_fields.items(), data)
                }

        return data


def get_list_child_model(model):
    if is_basic_list_type(model):
        # If not specified, list elements may be anything.
        # Without additional information, we assume strings.
        child_model = str
    else:
        # Get the type that's inside the list
        assert len(model.__args__) == 1
        child_model = model.__args__[0]
    return child_model


def is_list_type(model):
    """
    Determine whether model is a list type, such as list, list[str], List, List[str].

    typing.List is deprecated as of Python 3.9
    """
    return (
        is_basic_list_type(model)
        or model is List
        or getattr(model, "__origin__", None) is list
    )


def is_basic_list_type(model):
    return model is list


def is_basic_dict_type(model):
    return model is dict


def is_list_instance(value):
    return isinstance(value, list)


def is_iterable_instance(value):
    return isinstance(value, Iterable) and not type(value) is str


def is_parser_model_type(model):
    # Determine whether model is a subclass of ParserModel.
    try:
        return issubclass(model, ParserModel)
    except TypeError:
        # This occurs in Python >= 3.7 if one argument is a nested type, e.g. List[str]
        return False


def is_parser_model_instance(value):
    return isinstance(value, ParserModel)


def is_basic_type(model):
    return model in (str, int, float, bool)


def is_basic_instance(value):
    return isinstance(value, (str, int, float, bool))


def is_default_value(model_instance, field, field_value):
    return field_value == type(model_instance).model_fields[field].default


def str_to_bool(string):
    # in this case, the default value takes effect.
    if string.lower() == "false":
        return False
    else:
        return True


def get_field_name(string):
    return (
        string.split(RowParser.TYPE_ANNOTATION_SEPARATOR)[0]
        .split(RowParser.DEFAULT_VALUE_SEPARATOR)[0]
        .strip()
    )


class RowParser:
    # Takes a dictionary of cell entries, whose keys are the column names
    # and the values are the cell content converted into nested lists.
    # Turns this into an instance of the provided model.

    HEADER_FIELD_SEPARATOR = "."
    TYPE_ANNOTATION_SEPARATOR = ":"
    DEFAULT_VALUE_SEPARATOR = "="

    def __init__(self, model, cell_parser=None):
        self.model = model
        self.output = None  # Gets reinitialized with each call to parse_row
        self.cell_parser = cell_parser or CellParser()

    def try_assign_as_kwarg(self, field, key, value, model):
        # If value can be interpreted as a (field, field_value) pair for a field of
        # model, assign value to field[key] (which represents the field in the model)
        if is_list_instance(value) and len(value) == 2 and type(value[0]) is str:
            first_entry_as_key = model.header_name_to_field_name(value[0])
            if first_entry_as_key in model.model_fields:
                self.assign_value(
                    field[key],
                    first_entry_as_key,
                    value[1],
                    model.model_fields[first_entry_as_key].annotation,
                )
                return True
        return False

    def assign_value(self, field, key, value, model):
        # Given a field in the output and a key, assign
        # value (which can be a nested structure) to field[key].
        # This is done recursively, and
        # converts some lists into dicts in the process,
        # as appropriate and as determined by model,
        # which is the model/type of field[key]).
        # Note: field can also be a list and key an index.

        # Using both key and field here because if we passed field[key],
        # we can't do call by reference with basic types.
        if is_parser_model_type(model):
            # The value should be a dict/object
            field[key] = {}
            # Get the list of keys that are available for the target model
            # Note: The fields have a well defined ordering.
            # See https://pydantic-docs.helpmanual.io/usage/models/#field-ordering
            model_fields = list(model.model_fields.keys())

            if type(value) is not list:
                # It could be that an object is specified via a single element.
                value = [value]
            if self.try_assign_as_kwarg(field, key, value, model):
                # Check if value could encode a single KWArg; if yes, assign as such.
                # Note: We're resolving an ambiguity here in favor of kwargs.
                # in principle, this could also be two positional arguments.
                return

            for i, entry in enumerate(value):
                # Go through the list of arguments
                kwarg_found = False
                if self.try_assign_as_kwarg(field, key, entry, model):
                    # This looks like a KWArg
                    # Note: We're resolving an ambiguity here in favor of kwargs.
                    # in principle, this could also be a positional argument that is a
                    # list.
                    kwarg_found = True
                else:
                    # This isn't a KWarg, so we interpret is as a positional argument
                    # KWArgs should come after positional arguments --> assert
                    assert not kwarg_found
                    entry_key = model_fields[i]
                    self.assign_value(
                        field[key],
                        entry_key,
                        entry,
                        model.model_fields[entry_key].annotation,
                    )
        elif is_basic_dict_type(model):
            field[key] = {}
            if not value:
                return
            if not is_iterable_instance(value):
                raise ValueError("dict-type cell must contain key-value pairs")
            value = list(value)
            if isinstance(value[0], str):
                assert len(value) == 2
                field[key] = {value[0]: value[1]}
            elif isinstance(value[0], list):
                for entry in value:
                    assert len(entry) == 2
                    field[key][entry[0]] = entry[1]
        elif is_basic_list_type(model):
            # We cannot iterate deeper if we don't know what to expect.
            if is_iterable_instance(value):
                field[key] = list(value)
            else:
                field[key] = [value]
        elif is_list_type(model):
            child_model = get_list_child_model(model)
            # The created entry should be a list. Value should also be a list
            field[key] = []
            # Note: This makes a decision on how to resolve an ambiguity when the target
            # field is a list of lists, but the cell value is a 1-dimensional list.
            # 1;2 → [[1],[2]] rather than [[1,2]]
            if not is_list_instance(value):
                # It could be that a list is specified via a single element.
                if value == "":
                    # Interpret an empty cell as [] rather than ['']
                    value = []
                else:
                    value = [value]
            for entry in value:
                # For each entry, create a new list entry and assign its value
                # recursively
                field[key].append(None)
                self.assign_value(field[key], -1, entry, child_model)
        else:
            assert is_basic_type(model)
            # The value should be a basic type
            # TODO: Ensure the types match. E.g. we don't want value to be a list
            if model == bool:
                if type(value) is str:
                    stripped = value.strip()
                    # Special case: empty string is not assigned at all.
                    if stripped:
                        field[key] = str_to_bool(stripped)
                else:
                    field[key] = bool(value)
            else:
                field[key] = model(value)

    def find_entry(self, model, output_field, field_path):
        # Within the output_field (which may be a nested structure),
        # traverse the field_path to find the subfield to assign the value to.
        # Return that field (via a parent object and a key, so that we can
        # overwrite its value) and its model.

        # Note: model is the model/type that the output_field should correspond to
        # (though objects are modeled as dicts in the output). It helps us
        # traverse the path in output_field and if necessary create non-existent
        # entries.

        # We're creating the output object's fields as we're going through it.
        # It'd be nicer to already have a template.
        field_name = field_path[0]
        if is_list_type(model):
            child_model = get_list_child_model(model)
            index = int(field_name) - 1
            if len(output_field) <= index:
                # Create a new list entry for this, if necessary
                # We assume the columns are always in order 1, 2, 3, ... for now
                assert len(output_field) == index
                # None will later be overwritten by assign_value
                output_field.append(None)

            key = index
        elif is_basic_dict_type(model):
            key = field_name
            output_field[key] = None
            child_model = str
        else:
            assert is_parser_model_type(model)
            key = model.header_name_to_field_name(field_name)
            if key not in model.model_fields:
                raise ValueError(f"Field {key} doesn't exist in target type {model}.")
            child_model = model.model_fields[key].annotation

            if key not in output_field:
                # Create a new entry for this, if necessary
                # None will later be overwritten by assign_value
                output_field[key] = None

        if len(field_path) == 1:
            # We've reached the end of the field_path
            # Therefore we've found where we need to assign
            return output_field, key, child_model
        else:
            # The field has subfields, keep going and recurse.
            # If field doesn't exist yet in our output object, create it.
            if is_list_type(child_model) and output_field[key] is None:
                output_field[key] = []
            elif is_basic_dict_type(child_model) and output_field[key] is None:
                output_field[key] = {}
            elif is_parser_model_type(child_model) and output_field[key] is None:
                output_field[key] = {}
            # recurse
            return self.find_entry(child_model, output_field[key], field_path[1:])

    def parse_entry(
        self, column_name, value, value_is_parsed=False, template_context={}
    ):
        # This creates/populates a field in self.output
        # The field is determined by column_name, its value by value
        column_name = get_field_name(column_name)
        field_path = column_name.split(RowParser.HEADER_FIELD_SEPARATOR)
        # Find the destination subfield in self.output that corresponds to field_path
        field, key, model = self.find_entry(self.model, self.output, field_path)
        # The destination field in self.output is field[key], its type is model.
        # Therefore the value should be assigned to field[key].
        # (Note: This is a bit awkward; if we returned field[key] itself, we could
        # not easily overwrite its value. So we return field and key separately.
        # Ideally we would return a pointer to the destination field.
        # The model of field[key] is model, and thus value should also be interpreted
        # as being of type model.
        if not value_is_parsed:
            if (
                is_list_type(model)
                or is_basic_dict_type(model)
                or is_parser_model_type(model)
            ):
                # If the expected type of the value is list/object,
                # parse the cell content as such.
                # Otherwise leave it as a string
                value = self.cell_parser.parse(value, context=template_context)
            else:
                value, _ = self.cell_parser.parse_as_string(
                    value, context=template_context
                )
        self.assign_value(field, key, value, model)

    def parse_row(self, data, template_context={}):
        # data is a dict where the keys are column header names,
        # and the values are the corresponding values of the cells
        # in the spreadsheet (i.e. strings).
        # However, because we don't have the string parser yet,
        # the values are assumed to be parsed already, i.e. are
        # nested lists.

        # Initialize the output template as a dict
        self.output = {}

        # Apply map from header string to field specification
        data_rekeyed = {}
        for k, v in data.items():
            k = self.model.header_name_to_field_name_with_context(k, data)
            data_rekeyed[k] = v
        data = data_rekeyed

        # For each column with an asterisk (*) (indicating list of fields),
        # Compute how long the implied list is by taking the maximum
        # over the lengths of all fields that this list refers to.
        # Note: So far, no nested asterisks are supported.
        asterisk_list_lengths = defaultdict(lambda: 1)
        for k, v in data.items():
            if "*" in k:
                prefix = k.split("*")[0]
                parsed_v = self.cell_parser.parse(v, context=template_context)
                if isinstance(parsed_v, list):
                    asterisk_list_lengths[prefix] = max(
                        asterisk_list_lengths[prefix], len(parsed_v)
                    )
                    # No else case needed because then the implied list length is 1,
                    # i.e. the default value
        # Process each entry
        for k, v in data.items():
            if "*" in k:
                # Process each prefix:*:suffix column entry by assigning the individual
                # list values to prefix:1:suffix, prefix:2:suffix, etc
                prefix = k.split("*")[0]
                parsed_v = self.cell_parser.parse(v, context=template_context)
                if not isinstance(parsed_v, list):
                    # If there was only one entry, we assume it is used for the entire
                    # list
                    parsed_v = [parsed_v] * asterisk_list_lengths[prefix]
                for i, elem in enumerate(parsed_v):
                    self.parse_entry(
                        k.replace("*", str(i + 1)),
                        elem,
                        value_is_parsed=True,
                        template_context=template_context,
                    )
            else:
                # Normal, non-* column entry.
                self.parse_entry(k, v, template_context=template_context)
        # Returning an instance of the model rather than the output directly
        # helps us fill in default values where no entries exist.
        # Filtering out None values here is a bit of a hack;
        # the cause of these is the line output_field[key] = None in find_key.
        # Ideally, we should fix the cause rather than clean up here.
        self.output = {k: v for k, v in self.output.items() if v is not None}
        return self.model(**self.output)

    def unparse_row(self, model_instance, target_headers=set(), excluded_headers=set()):
        """
        Turn a model instance into spreadsheet row.

        Args:
            model_instance (ParserModel): model instance to convert
            target_headers (set[str]): Complex type fields (ParserModels, lists, dicts)
                whose content should be represented in the output dict as a single
                entry. A trailing asterisk may be used to specify multiple fields
                at once, such as `list.*` and `field.*`.
            excluded_headers (set[str]): Fields to exclude from the output. Same format
                as target_headers.

        Returns:
            A flat dict[str,str] where the keys reference fields of the model
            and the values string representations of the values of the fields.
            Keys can also reference subfields, for example, if the model has a
            field `field` whose type is another model which has a field `subfield`,
            then `field.subfield` would be a valid key referencing this subfield.
            Similarly, `list.1` can reference to the first element of a list.
            By default, all model content is unravelled until the referenced fields
            are basic types. However, `target_headers` can be used to specify
            complex type fields (ParserModels, lists, dicts) whose content should be
            represented as a single string.
        """
        self.output_dict = {}
        self.unparse_row_recurse(model_instance, "", target_headers, excluded_headers)
        return self.output_dict

    def trim_prefix(self, prefix):
        # We have to remove the leading '.' from the prefix, if necessary
        if prefix.startswith("."):
            return prefix[1:]
        return prefix

    def write_to_output_dict(self, prefix, value):
        if not is_basic_instance(value):
            value_list = self.to_nested_list(value)
            value = self.cell_parser.join_from_lists(value_list)
        prefix = self.trim_prefix(prefix)
        if prefix in self.output_dict:
            old_value = self.output_dict[prefix]
            raise RowParserError(
                f'Unparse: Multiple entries ("{old_value}" and "{value}") '
                f'with same key "{prefix}."'
            )
        self.output_dict[prefix] = value

    def unparse_row_recurse(
        self, value, prefix, target_headers=set(), excluded_headers=set()
    ):
        if value is None or self.matches_headers(prefix, excluded_headers):
            return

        if is_basic_instance(value) or self.matches_headers(prefix, target_headers):
            self.write_to_output_dict(prefix, value)
        elif is_list_instance(value):
            for i, entry in enumerate(value):
                self.unparse_row_recurse(
                    entry,
                    f"{prefix}{RowParser.HEADER_FIELD_SEPARATOR}{i+1}",
                    target_headers,
                    excluded_headers,
                )
        elif is_parser_model_instance(value):
            for field, field_value in value:
                if is_default_value(value, field, field_value):
                    continue
                mapped_field = type(value).field_name_to_header_name(field)
                field_prefix = (
                    f"{prefix}{RowParser.HEADER_FIELD_SEPARATOR}{mapped_field}"
                )
                if field == mapped_field:
                    # No remapping happened
                    self.unparse_row_recurse(
                        field_value,
                        field_prefix,
                        target_headers,
                        excluded_headers,
                    )
                else:
                    # If a remapping occurs, we allow no further recursion.
                    # We would get inconsistencies where e.g. if we map a list
                    # and a string to the same key `mapped_field`, the string
                    # might generate a column `mapped_field` while the list may
                    # generated columns `mapped_field.1` and `mapped_field.2`.
                    if not self.matches_headers(field_prefix, excluded_headers):
                        self.write_to_output_dict(field_prefix, field_value)
        else:
            raise ValueError(f"Unsupported field type {type(value)} of {value}.")

    def matches_headers(self, prefix, target_headers):
        if not prefix:
            return False
        prefix = self.trim_prefix(prefix)
        # Examples:
        #     a.b.field matches a.b.field
        #     list.1 matches list.1
        #     list.1 matches list.*
        #     list.1.field matches list.*.field
        #     dict.field matches dict.*
        # Technically, x.field.subfield matches x.field; however, such a comparison
        # will never occur in unparse_row_recurse because once x.field is encountered,
        # the recursion bottoms out (because x.field matches x.field) and does not
        # proceed to process the x.field.subfield prefix.
        for header in target_headers:
            header_regex = "^" + header.replace(".", "\\.").replace("*", "[^.]+")
            pattern = re.compile(header_regex)
            if pattern.match(prefix):
                return True
        return False

    def to_nested_list(self, value):
        if is_basic_instance(value):
            return value
        elif is_list_instance(value):
            return [self.to_nested_list(e) for e in value]
        elif is_parser_model_instance(value):
            # We're encoding key-value pairs here, which takes a nesting depth of 2.
            # We could also consider encoding as positional arguments, however,
            # this is not reversible in the case where there are exactly two values,
            # and first value coincides with the name of a model attribute.
            value_dict = dict(value)
            # Remove default values
            value_dict = {
                field: field_value
                for field, field_value in value_dict.items()
                if not is_default_value(value, field, field_value)
            }
            return [[k, self.to_nested_list(v)] for k, v in value_dict.items()]
