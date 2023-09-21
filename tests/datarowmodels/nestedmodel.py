from rpft.parsers.creation.datarowmodel import DataRowModel
from rpft.parsers.common.rowparser import ParserModel


class CustomModel(ParserModel):
    # Because this does not directly define the content of a datasheet,
    # in inherits from ParserModel and not DataRowModel.
    happy: str = ""
    sad: str = ""


class NestedRowModel(DataRowModel):
    # Because this defines the content of a datasheet,
    # it inherits DataRowModel, which gives it the ID column.
    value1: str = ""
    custom_field: CustomModel = CustomModel()  # Default value is an empty custom model
