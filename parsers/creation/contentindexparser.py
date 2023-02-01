import importlib
from collections import OrderedDict
from .contentindexrowmodel import ContentIndexRowModel
from parsers.common.cellparser import CellParser
from parsers.common.sheetparser import SheetParser
from parsers.common.rowparser import RowParser
from rapidpro.models.containers import RapidProContainer
from parsers.creation.flowparser import FlowParser


class TemplateSheet:
	def __init__(self, table, argument_definitions):
		self.table = table
		self.argument_definitions = argument_definitions


class ContentIndexParser:

	def  __init__(self, sheet_reader, user_data_model_module_name=None):
		self.sheet_reader = sheet_reader
		self.template_sheets = {}  # values: tablib tables
		self.data_sheets = {}  # values: OrderedDicts of RowModels
		self.flow_definition_rows = []  # list of ContentIndexRowModel
		if user_data_model_module_name:
			self.user_models_module = importlib.import_module(user_data_model_module_name)
		main_sheet = self.sheet_reader.get_main_sheet()
		self.process_content_index_table(main_sheet)

	def process_content_index_table(self, content_index_table):
		# content_index_table is in tablib table format
		row_parser = RowParser(ContentIndexRowModel, CellParser())
		sheet_parser = SheetParser(row_parser, content_index_table)
		content_index_rows = sheet_parser.parse_all()
		for row in content_index_rows:
			if row.status == 'draft':
				continue
			if row.type == 'content_index':
				assert len(row.sheet_name) == 1
				sheet_name = row.sheet_name[0]
				sheet = self.sheet_reader.get_sheet(sheet_name)
				self.process_content_index_table(sheet)
			elif row.type == 'data_sheet':
				assert len(row.sheet_name) >= 1
				self.process_data_sheet(row.sheet_name, row.new_name, row.data_model)
			elif row.type in ['template_definition', 'create_flow']:
				assert len(row.sheet_name) == 1
				sheet_name = row.sheet_name[0]
				if sheet_name not in self.template_sheets:
					sheet = self.sheet_reader.get_sheet(sheet_name)
					self.template_sheets[sheet_name] = TemplateSheet(sheet, row.template_argument_definitions)
				if row.type == 'create_flow':
					self.flow_definition_rows.append(row)
			else:
				raise ValueError(f'ContentIndex has row with invalid type: {row.type}.')

	def process_data_sheet(self, sheet_names, new_name, data_model_name):
		if not hasattr(self, 'user_models_module'):
			raise ValueError("If there are data sheets, a user_data_model_module_name has to be provided")
		if len(sheet_names) > 1 and not new_name:
			raise ValueError("If multiple sheet are concatenated, a new_name has to be provided")
		if not new_name:
			new_name = sheet_names[0]
		content = OrderedDict()
		for sheet_name in sheet_names:
			data_table = self.sheet_reader.get_sheet(sheet_name)
			user_model = getattr(self.user_models_module, data_model_name)
			row_parser = RowParser(user_model, CellParser())
			sheet_parser = SheetParser(row_parser, data_table)
			data_rows = sheet_parser.parse_all()
			sheet_content = OrderedDict((row.ID, row) for row in data_rows)
			content.update(sheet_content)
		self.data_sheets[new_name] = content

	def get_data_model_instance(self, sheet_name, row_id):
		return self.data_sheets[sheet_name][row_id]

	def get_all_data_model_instances(self, sheet_name):
		return self.data_sheets[sheet_name]

	def get_template_sheet(self, name):
		return self.template_sheets[name]

	def get_node_group(self, template_name, data_sheet, data_row_id, template_arguments):
		# TODO: Factor out logic duplication between this function and parse_all_flows.
		if (data_sheet and data_row_id) or (not data_sheet and not data_row_id):
			flow_name = template_name  # = row.new_name or row.sheet_name
			return self.parse_flow(template_name, data_sheet, data_row_id, template_arguments, RapidProContainer(), parse_as_block=True)
		else:
			raise ValueError(f'For insert_as_block, either both data_sheet and data_row_id or neither have to be provided.')		

	def parse_all_flows(self):
		rapidpro_container = RapidProContainer()
		# sheet_name = row.new_name or row.sheet_name
		for row in self.flow_definition_rows:
			if row.data_sheet and not row.data_row_id:
				data_rows = self.get_all_data_model_instances(row.data_sheet)
				for data_row_id in data_rows.keys():
					self.parse_flow(row.sheet_name[0], row.data_sheet, data_row_id, row.template_arguments, rapidpro_container)
			elif not row.data_sheet and row.data_row_id:
				raise ValueError(f'For create_flow, if data_row_id is provided, data_sheet must also be provided.')
			else:
				self.parse_flow(row.sheet_name[0], row.data_sheet, row.data_row_id, row.template_arguments, rapidpro_container)
		return rapidpro_container	

	def parse_flow(self, sheet_name, data_sheet, data_row_id, template_arguments, rapidpro_container, parse_as_block=False):
		if data_sheet and data_row_id:
			flow_name = ' - '.join([sheet_name, data_row_id])
			context = self.get_data_model_instance(data_sheet, data_row_id)
		else:
			assert not data_sheet and not data_row_id
			flow_name = sheet_name
			context = {}
		template_sheet = self.get_template_sheet(sheet_name)
		template_table = template_sheet.table
		template_argument_definitions = template_sheet.argument_definitions
		context = dict(context)
		self.map_template_arguments_to_context(template_argument_definitions, template_arguments, context)
		flow_parser = FlowParser(rapidpro_container, flow_name, template_table, context=context, content_index_parser=self)
		if parse_as_block:
			return flow_parser.parse_as_block()
		else:
			return flow_parser.parse()
		# Is automatically added to the rapidpro_container, for now.

	def map_template_arguments_to_context(self, arg_defs, args, context):
		# Template arguments are positional arguments.
		# This function maps them to the arguments from the template
		# definition, and adds the values of the arguments to the context
		# with the appropriate variable name (from the definition)
		if len(args) > len(arg_defs):
			# Check if these args are non-empty.
			# Once the row parser is cleaned up to eliminate trailing ''
			# entries, this won't be necessary
			extra_args = args[len(arg_defs):]
			non_empty_extra_args = [ea for ea in extra_args if ea]
			if non_empty_extra_args:
				raise ValueError('Too many arguments provided to template')
			# All extra args are blank. Truncate them
			args = args[:len(arg_defs)]
		args_padding = [''] * (len(arg_defs) - len(args))
		for arg_def, arg in zip(arg_defs, args + args_padding):
			if arg_def.name in context:
				raise ValueError(f'Template argument "{arg_def.name}" doubly defined in context')
			arg_value = arg or arg_def.default_value
			if not arg_value:
				raise ValueError(f'Required template argument "{arg_def.name}" not provided')
			if arg_def.type == 'sheet':
				context[arg_def.name] = self.data_sheets[arg_value]
			else:
				context[arg_def.name] = arg_value
