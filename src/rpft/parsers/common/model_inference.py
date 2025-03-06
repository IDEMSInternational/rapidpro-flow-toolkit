from collections import defaultdict
from typing import List, ForwardRef, _eval_type
from pydoc import locate
from pydantic import create_model

from rpft.parsers.common.rowparser import (
    ParserModel,
    RowParser,
    RowParserError,
    get_field_name,
    is_list_type,
    is_parser_model_type,
    str_to_bool,
)


def type_from_string(string):
    if not string:
        # By default, assume str
        return str
    basic_type = locate(string)
    if basic_type:
        return basic_type
    try:
        inferred_type = _eval_type(ForwardRef(string), globals(), globals())
    except NameError as e:
        raise RowParserError(f'Error while parsing type "{string}": {str(e)}')
    return inferred_type


def get_value_for_type(type, value=None):
    if is_list_type(type):
        # We do not support default values for lists.
        return []
    if is_parser_model_type(type):
        # We do not support default values for ParserModel.
        return type()
    if value is not None:
        if type is bool:
            return str_to_bool(value)
        return type(value)
    return type()


def infer_type(string):
    if RowParser.TYPE_ANNOTATION_SEPARATOR not in string:
        return type_from_string("")
    # Take the stuff between colon and equal sign
    prefix, suffix = string.split(RowParser.TYPE_ANNOTATION_SEPARATOR, 1)
    return type_from_string(suffix.split(RowParser.DEFAULT_VALUE_SEPARATOR)[0].strip())


def infer_default_value(type, string):
    if RowParser.DEFAULT_VALUE_SEPARATOR not in string:
        # Return the default value for the given type
        return get_value_for_type(type)
    prefix, suffix = string.split(RowParser.DEFAULT_VALUE_SEPARATOR, 1)
    return get_value_for_type(type, suffix.strip())


def parse_header_annotations(string):
    inferred_type = infer_type(string)
    return inferred_type, infer_default_value(inferred_type, string)


def represents_integer(string):
    try:
        _ = int(string)
        return True
    except ValueError:
        return False


def dict_to_list(dict):
    out = [None] * (max(dict.keys()) + 1)
    for k, v in dict.items():
        out[k] = v
    return out


def model_from_headers(name, headers):
    return model_from_headers_rec(name, headers)[0]


def model_from_headers_rec(name, headers):
    # Returns a model and a default value
    fields = {}
    complex_fields = defaultdict(list)
    for header in headers:
        if RowParser.HEADER_FIELD_SEPARATOR in header:
            field, subheader = header.split(RowParser.HEADER_FIELD_SEPARATOR, 1)
            complex_fields[field].append(subheader)
        else:
            field = get_field_name(header)
            field_type, default_value = parse_header_annotations(header)
            fields[field] = (field_type, default_value)
    for field, subheaders in complex_fields.items():
        # Assign model and default value
        fields[field] = model_from_headers_rec(name.title() + field.title(), subheaders)

    # In case the model that we're creating is a list,
    # all its fields are numbers (indices).
    list_model = None
    list_default_values = {}
    for field, value in fields.items():
        if represents_integer(field):
            # We do not check whether the models for each list entry match.
            # We just take one of them.
            list_model = value[0]
            # Index shift: because in the headers, we count from 1
            list_default_values[int(field) - 1] = value[1]
    if list_model is not None:
        return List[list_model], dict_to_list(list_default_values)

    # If the model we're creating is not a list, it's a class
    model = create_model(name.title(), __base__=ParserModel, **fields)
    return model, get_value_for_type(model)
