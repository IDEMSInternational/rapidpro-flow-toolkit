from rpft.parsers.creation.datarowmodel import DataRowModel
from typing import List


class ListRowModel(DataRowModel):
    # Because this defines the content of a datasheet,
    # it inherits DataRowModel, which gives it the ID column.
    messages: List[str]


class LookupRowModel(DataRowModel):
    # Because this defines the content of a datasheet,
    # it inherits DataRowModel, which gives it the ID column.
    happy: str
    sad: str
    neutral: str
