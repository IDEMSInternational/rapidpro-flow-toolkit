import re
from collections import defaultdict

from rapidpro.models.actions import SendMessageAction, SetContactFieldAction, AddContactGroupAction, \
    RemoveContactGroupAction, SetRunResultAction, Group
from rapidpro.models.containers import Container
from rapidpro.models.nodes import BaseNode, BasicNode, SwitchRouterNode
from parsers.common.cellparser import get_object_from_cell_value, get_separators


class Parser:

    def __init__(self, container, data_rows, flow_name=None):
        self.container = container or Container(flow_name=flow_name)
        self.data_rows = data_rows

        self.sheet_map = defaultdict()
        for row in self.data_rows:
            self.sheet_map[row.row_id] = row

        self.row_id_to_node_map = defaultdict()
        self.node_name_to_node_map = defaultdict()
        self.group_name_to_group_map = defaultdict()

    def parse(self):
        for row in self.data_rows:
            self._parse_row(row)

    def get_row_action(self, row):
        attachment_types = [row.image, row.audio, row.video]
        if row.type == 'send_message':
            send_message_action = SendMessageAction(text=row.mainarg_message_text)
            for attachment in [row.image, row.audio, row.video]:
                if attachment:
                    send_message_action.add_attachment(attachment)

            quick_replies = [qr for qr in row.choices if qr]
            if quick_replies:
                for qr in quick_replies:
                    send_message_action.add_quick_reply(qr)
            return send_message_action

        elif row.type == 'save_value':
            set_contact_field_action = SetContactFieldAction(field_name=row.save_name, value=row.mainarg_value)
            return set_contact_field_action

        elif row.type == 'add_to_group':
            group = self._get_or_create_group(row)
            add_group_action = AddContactGroupAction(groups=[group])
            return add_group_action

        elif row.type == 'remove_from_group':
            group = self._get_or_create_group(row)
            remove_group_action = RemoveContactGroupAction(groups=[group])
            return remove_group_action

        elif row.type == 'save_flow_result':
            set_run_result_action = SetRunResultAction(row.save_name, row.mainarg_value, category=None)
            return set_run_result_action

        else:
            print(f'Row type {row.type} not implemented')

    def _get_or_create_group(self, row):
        existing_group = self.group_name_to_group_map.get(self.get_object_name(row))
        if existing_group:
            return existing_group

        new_group = Group(name=row.mainarg_groups[0])  # TODO: support lists
        self.group_name_to_group_map[self.get_object_name(row)] = new_group

        return new_group

    def get_row_node(self, row):
        if row.type in ['send_message', 'save_value', 'add_to_group', 'remove_from_group', 'save_flow_result']:
            node = BasicNode()
            node.update_default_exit(None)
            return node
        elif row.type in ['start_new_flow']:
            node = SwitchRouterNode(operand='@input.text')
            for edge in row.edges:
                condition = edge.condition
                if condition.value:
                    node.add_choice(
                        comparison_variable=condition.variable or '@input.text',
                        comparison_type=condition.type or 'has_any_word',
                        comparison_arguments=[condition.value],
                        category_name=condition.name or 'Other',
                        category_destination_uuid=None,
                        is_default=True
                    )
            return node

        else:
            return BasicNode()

    def get_object_name(self, row):
        return row.obj_id or row.obj_name

    def get_node_name(self, row):
        return row.node_uuid or row.node_name

    def _get_last_node(self):
        try:
            return self.container.nodes[-1]
        except IndexError:
            return None

    def _find_destination_node_row_id(self, origin_row_id, condition):
        for row_id, row in self.sheet_map.items():
            separator_1, _, _ = get_separators(row['from'])
            for from_row_id in row['from'].split(separator_1):
                if from_row_id == origin_row_id and row['condition'] == condition:
                    return self.row_id_to_node_map()

    def _find_node_with_conditional_exit(self, row_id, condition):
        row = self.sheet_map[row_id]
        condition_columns = [key for key in row.keys() if key.startswith('condition:')]
        for column_name in condition_columns:
            if row[column_name]:
                condition_obj = get_object_from_cell_value(row[column_name])
                if condition_obj['condition'] == condition:
                    pass

        valid_conditions = [get_object_from_cell_value(row[column_name]) for column_name in condition_columns if
                            row[column_name]]
        return valid_conditions

    def _parse_row(self, row):
        row_action = self.get_row_action(row)
        node_name = self.get_node_name(row)
        existing_node = self.node_name_to_node_map.get(node_name)

        if node_name and existing_node:
            existing_node.add_action(row_action)
            self.row_id_to_node_map[row.row_id] = existing_node
        else:
            new_node = self.get_row_node(row)

            if row_action:
                new_node.add_action(row_action)

            from_row_ids = [edge.from_ for edge in row.edges]

            for from_id in from_row_ids:
                if from_id != 'start':
                    from_nodes = [self.row_id_to_node_map[row_id] for row_id in from_row_ids]
                    for node in from_nodes:
                        node.update_default_exit(new_node.uuid)

            self.container.add_node(new_node)

            self.row_id_to_node_map[row.row_id] = new_node
            self.node_name_to_node_map[self.get_node_name(row)] = new_node
