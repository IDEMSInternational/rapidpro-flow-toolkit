import re
from collections import defaultdict

from rapidpro.models.actions import SendMessageAction, SetContactFieldAction, AddContactGroupAction, \
    RemoveContactGroupAction, SetRunResultAction, Group
from rapidpro.models.containers import Container
from rapidpro.models.nodes import BaseNode, BasicNode, SwitchRouterNode, RandomRouterNode, EnterFlowNode
from rapidpro.models.routers import SwitchRouter, RandomRouter
from parsers.common.cellparser import get_object_from_cell_value, get_separators
from .standard_models import Condition


class NodeGroup:
    def __init__(self, node):
        '''node: first node in the group'''
        self.nodes = [node]

    def entry_node(self):
        return self.nodes[0]

    def exit_node(self):
        return self.nodes[-1]

    def add_exit(self, destination_uuid, condition):
        created_node = None
        exit_node = self.exit_node()
        # Unconditional/default case edge
        if condition == Condition() and not isinstance(exit_node, RandomRouterNode):
            # For BasicNode, this updates the default exit.
            # For SwitchRouterNode, this updates the exit of the default category.
            # For EnterFlowNode, this should throw an error.
            exit_node.update_default_exit(destination_uuid)
            return

        # Completed/Expired edge from start_new_flow
        if isinstance(exit_node, EnterFlowNode):
            if condition.variable.lower() in ['complete', 'completed']:
                exit_node.update_completed_exit(destination_uuid)
            elif condition.variable.lower() == 'expired':
                exit_node.update_expired_exit(destination_uuid)
            else:
                raise ValueError("Condition from start_new_flow must be 'Completed' or 'Expired'.")

        # We have a non-trivial condition. Fill in default values if necessary
        if not condition.variable:
            # TODO: Check if the source node has a save_name, and use that instead
            wait_for_message = True
            variable = '@input.text'
        else:
            wait_for_message = False
            variable = condition.variable

        if isinstance(exit_node, BasicNode):
            # We have a basic node, but a non-trivial condition.
            old_exit_node = exit_node
            old_destination = old_exit_node.default_exit.destination_uuid
            exit_node = SwitchRouterNode(variable, wait_for_message=wait_for_message)
            exit_node.update_default_exit(old_destination)
            old_exit_node.update_default_exit(exit_node.uuid)
            self.nodes.append(exit_node)
            created_node = exit_node

        # Add an outgoing edge to the router
        if isinstance(exit_node.router, SwitchRouter):
            exit_node.add_choice(
                comparison_variable=variable,
                comparison_type=condition.type or 'has_any_word',
                comparison_arguments=[condition.value],
                category_name=condition.name,
                destination_uuid=destination_uuid,
                is_default=False
            )
        else:  # Random router
            exit_node.add_choice(
                category_name=condition.name or condition.value,
                destination_uuid=destination_uuid
            )

        return created_node


class Parser:

    def __init__(self, container, data_rows, flow_name=None):
        self.container = container or Container(flow_name=flow_name)
        self.data_rows = data_rows

        self.sheet_map = defaultdict()
        for row in self.data_rows:
            self.sheet_map[row.row_id] = row

        self.row_id_to_nodegroup = defaultdict()
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
            return node
        else:
            # TODO.
            # I believe it's possible to store the random router value
            # --> implement save name
            return BasicNode()

    def get_object_name(self, row):
        return row.obj_id or row.obj_name

    def get_node_name(self, row):
        return row.node_uuid or row.node_name

    def _parse_row(self, row):
        row_action = self.get_row_action(row)
        node_name = self.get_node_name(row)
        existing_node = self.node_name_to_node_map.get(node_name)

        if node_name and existing_node:
            # If we want to add an action to an existing node of a given name,
            # there must be exactly one unconditional edge, and the
            # from_ row_id has to match.
            if len(row.edges) == 1 and row.edges[0].condition == Condition() and self.row_id_to_nodegroup.get(row.edges[0].from_).entry_node() == existing_node:
                existing_node.add_action(row_action)
                self.row_id_to_nodegroup[row.row_id] = self.row_id_to_nodegroup[row.edges[0].from_]
                return
            else:
                print(f'Cannot merge rows using node name {node_name} into a single node.')

        new_node = self.get_row_node(row)
        if row_action:
            new_node.add_action(row_action)

        for edge in row.edges:
            if edge.from_ != 'start':
                from_node_group = self.row_id_to_nodegroup[edge.from_]
                created_node = from_node_group.add_exit(new_node.uuid, edge.condition)
                if created_node:
                    self.container.add_node(created_node)                    

        self.container.add_node(new_node)
        self.row_id_to_nodegroup[row.row_id] = NodeGroup(new_node)
        self.node_name_to_node_map[self.get_node_name(row)] = new_node
