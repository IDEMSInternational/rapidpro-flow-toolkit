import re
from collections import defaultdict

from rapidpro.models.actions import SendMessageAction, SetContactFieldAction, AddContactGroupAction, \
    RemoveContactGroupAction, SetRunResultAction, Group
from rapidpro.models.containers import FlowContainer
from rapidpro.models.nodes import BaseNode, BasicNode, SwitchRouterNode, RandomRouterNode, EnterFlowNode
from rapidpro.models.routers import SwitchRouter, RandomRouter
from parsers.common.cellparser import CellParser
from parsers.common.rowparser import RowParser
from parsers.creation.standard_models import RowData
from .standard_models import Condition

class NodeGroup:
    def __init__(self, node, row_type):
        '''node: first node in the group'''
        self.nodes = [node]
        self.row_type = row_type

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
            if condition.value.lower() in ['complete', 'completed']:
                exit_node.update_completed_exit(destination_uuid)
            elif condition.value.lower() == 'expired':
                exit_node.update_expired_exit(destination_uuid)
            else:
                raise ValueError("Condition from start_new_flow must be 'Completed' or 'Expired'.")
            return

        # No Response edge from wait_for_response
        if isinstance(exit_node, SwitchRouterNode) and condition.value.lower() == "no response":
            if exit_node.has_positive_wait():
                exit_node.update_no_response_exit(destination_uuid)
            else:
                # TODO: Should this be a warning rather than an error?
                raise ValueError("No Response exit only exists for wait_for_response rows with non-zero timeout.")

        # We have a non-trivial condition. Fill in default values if necessary
        condition_type = condition.type
        comparison_arguments=[condition.value]
        wait_timeout = None
        if self.row_type in ['split_by_group', 'split_by_value']:
            variable = exit_node.router.operand
            if self.row_type == 'split_by_group':
                # Should such defaults be initialized as part of the data model?
                condition_type = 'has_group'
                # TODO: Validation step that fills in group/flow uuids
                comparison_arguments = [None, condition.value]
        elif condition.variable:
            variable = condition.variable
        else:
            # TODO: Check if the source node has a save_name, and use that instead?
            wait_timeout = 0
            variable = '@input.text'

        if isinstance(exit_node, BasicNode):
            # We have a basic node, but a non-trivial condition.
            # Create a router node (new exit_node) and connect it.
            old_exit_node = exit_node
            old_destination = old_exit_node.default_exit.destination_uuid
            exit_node = SwitchRouterNode(variable, wait_timeout=wait_timeout)
            exit_node.update_default_exit(old_destination)
            old_exit_node.update_default_exit(exit_node.uuid)
            self.nodes.append(exit_node)
            created_node = exit_node

        # Add an outgoing edge to the router
        if isinstance(exit_node.router, SwitchRouter):
            exit_node.add_choice(
                comparison_variable=variable,
                comparison_type=condition_type or 'has_any_word',
                comparison_arguments=comparison_arguments,
                category_name=condition.name,
                destination_uuid=destination_uuid,
                is_default=False
            )
        else:  # Random router
            # TODO: If a value is provided, respect the ordering provided there
            exit_node.add_choice(
                category_name=condition.name or condition.value,
                destination_uuid=destination_uuid
            )

        return created_node


class Parser:

    def __init__(self, rapidpro_container, rows, flow_name, flow_uuid=None):
        '''
        rapidpro_container: The parent RapidProContainer to contain the flow generated by this parser.
        rows: The sheet rows generating the flow.
        '''
        self.rapidpro_container = rapidpro_container
        self.flow_container = FlowContainer(flow_name=flow_name, uuid=flow_uuid)
        self.rapidpro_container.record_flow_uuid(flow_name, self.flow_container.uuid)
        row_parser = RowParser(RowData, CellParser())
        self.data_rows = [row_parser.parse_row(row) for row in rows]

        self.sheet_map = defaultdict()
        for row in self.data_rows:
            self.sheet_map[row.row_id] = row

        self.row_id_to_nodegroup = defaultdict()
        self.node_name_to_node_map = defaultdict()

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
            group = self._get_or_create_group(row.mainarg_groups[0], row.obj_id)
            add_group_action = AddContactGroupAction(groups=[group])
            return add_group_action
        elif row.type == 'remove_from_group':
            group = self._get_or_create_group(row.mainarg_groups[0], row.obj_id)
            remove_group_action = RemoveContactGroupAction(groups=[group])
            return remove_group_action
        elif row.type == 'save_flow_result':
            set_run_result_action = SetRunResultAction(row.save_name, row.mainarg_value, category=None)
            return set_run_result_action
        elif row.type in ['wait_for_response', 'split_by_value', 'split_by_group', 'split_random', 'start_new_flow']:
            return None
        else:
            print(f'Row type {row.type} not implemented')

    def _get_or_create_group(self, name, uuid=None):
        # TODO: support lists of groups
        if not uuid:
        # This shouldn't be necessary, but we keep it until we
        # have tests checking for group UUIDs.
            uuid = None
        return Group(name=name, uuid=uuid)

    def get_row_node(self, row):
        if row.type in ['add_to_group', 'remove_from_group', 'split_by_group'] and row.obj_id:
            self.rapidpro_container.record_group_uuid(row.mainarg_groups[0], row.obj_id)

        node_uuid = row.node_uuid or None
        if row.type in ['send_message', 'save_value', 'add_to_group', 'remove_from_group', 'save_flow_result']:
            node = BasicNode(uuid=node_uuid)
            node.update_default_exit(None)
            return node
        elif row.type in ['start_new_flow']:
            if row.obj_id:
                self.rapidpro_container.record_flow_uuid(row.mainarg_flow_name, row.obj_id)
            return EnterFlowNode(row.mainarg_flow_name, uuid=node_uuid)
        elif row.type in ['wait_for_response']:
            if row.no_response:
                return SwitchRouterNode('@input.text', result_name=row.save_name, wait_timeout=int(row.no_response), uuid=node_uuid)
            else:
                return SwitchRouterNode('@input.text', result_name=row.save_name, wait_timeout=None, uuid=node_uuid)
        elif row.type in ['split_by_value']:
            return SwitchRouterNode(row.mainarg_expression, result_name=row.save_name, wait_timeout=None, uuid=node_uuid)
        elif row.type in ['split_by_group']:
            return SwitchRouterNode('@contact.groups', result_name=row.save_name, wait_timeout=None, uuid=node_uuid)
        elif row.type in ['split_random']:
            return RandomRouterNode(result_name=row.save_name, uuid=node_uuid)
        else:
            return BasicNode(uuid=node_uuid)

    def get_node_name(self, row):
        return row.node_uuid or row.node_name

    def _add_row_edge(self, edge, destination_uuid):
        if edge.from_ != 'start':
            from_node_group = self.row_id_to_nodegroup[edge.from_]
            created_node = from_node_group.add_exit(destination_uuid, edge.condition)
            if created_node:
                self.flow_container.add_node(created_node)

    def _parse_goto_row(self, row):
        # If there is a single destination, connect all edges to that destination.
        # If not, ensure the number of edges and destinations match.
        destination_row_ids = row.mainarg_destination_row_ids
        if len(destination_row_ids) == 1:
            destination_row_ids = row.mainarg_destination_row_ids * len(row.edges)
        assert len(row.edges) == len(destination_row_ids)

        for edge, destination_row_id in zip(row.edges, destination_row_ids):
            destination_node_group = self.row_id_to_nodegroup[destination_row_id]
            self._add_row_edge(edge, destination_node_group.entry_node().uuid)

    def _parse_row(self, row):
        if row.type == 'go_to':
            self._parse_goto_row(row)
            return

        row_action = self.get_row_action(row)
        node_name = self.get_node_name(row)
        existing_node = self.node_name_to_node_map.get(node_name)

        if node_name and existing_node and row_action:
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
            self._add_row_edge(edge, new_node.uuid)

        # TODO: Rather than adding individual nodes to the container,
        # it might be cleaner to go through the list of NodeGroups at
        # the end and compile the list of nodes.
        # Caveat: Need to identify which is the starting node.
        self.flow_container.add_node(new_node)
        self.row_id_to_nodegroup[row.row_id] = NodeGroup(new_node, row.type)
        self.node_name_to_node_map[self.get_node_name(row)] = new_node

    def get_flow(self):
        '''
        Referenced groups or other flows may have a UUID which is None.
        Add the flow to a RapidProContainer and run update_global_uuids
        to fill in these missing UUIDs in a consistent way.
        '''
        return self.flow_container