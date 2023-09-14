from rpft.parsers.creation.datarowmodel import DataRowModel


class EvalMetadataModel(DataRowModel):
    include_if: str = ""


class EvalContentModel(DataRowModel):
    text: str = ""
