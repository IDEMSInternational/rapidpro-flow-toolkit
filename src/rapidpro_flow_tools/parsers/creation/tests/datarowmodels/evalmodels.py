from rapidpro_flow_tools.parsers.creation.datarowmodel import DataRowModel

class EvalMetadataModel(DataRowModel):
	include_if: str = ''

class EvalContentModel(DataRowModel):
	text: str = ''
