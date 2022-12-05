import re
import json
from collections import defaultdict

from rapidpro.models.actions import SendMessageAction, SetContactFieldAction, AddContactGroupAction, \
    RemoveContactGroupAction, SetRunResultAction, Group
from rapidpro.models.containers import FlowContainer
from rapidpro.models.nodes import BaseNode, BasicNode, SwitchRouterNode, RandomRouterNode, EnterFlowNode
from rapidpro.models.routers import SwitchRouter, RandomRouter
from parsers.common.cellparser import CellParser
from parsers.common.sheetparser import SheetParser
from parsers.common.rowparser import RowParser
from parsers.creation.flowrowmodel import FlowRowModel
from .flowrowmodel import Condition


class NodeGroup:
    # NodeGroups may have multiple exit nodes.
    # add_exit connects ALL of them, except for those
    # which are marked as hard exits
    # (which are not tracked as loose_exits)

    def __init__(self):
        # node_groups may contain NodeGroups and RowNodeGroups
        self.node_groups = []

    def is_empty(self):
        return self.node_groups == []

    def entry_node(self):
        return self.node_groups[0].entry_node()

    def last_node_group(self):
        return self.node_groups[-1]

    def has_loose_exits(self):
        for node_group in self.node_groups:
            if node_group.has_loose_exits():
                return True
        return False

    def add_exit(self, destination_uuid, condition):
        if condition != Condition():
            raise ValueError('Cannot attach conditional edges to a block.')
        if not self.has_loose_exits():
            raise ValueError('Block has no loose exit to connect to.')
        for node_group in self.node_groups:
            if node_group.has_loose_exits():
                node_group.connect_loose_exits(destination_uuid)

    def connect_loose_exits(self, destination_uuid):
        for node_group in self.node_groups:
            node_group.connect_loose_exits(destination_uuid)

    def add_node_group(self, node_group):
        # Node: Connecting of exits is not done here.
        self.node_groups.append(node_group)

    def add_nodes_to_flow(self, flow_container):
        for node in self.node_groups:
            node.add_nodes_to_flow(flow_container)


class NoOpNodeGroup:
    # TODO: Support ui_pos, in case there's a node.

    class ParentEdge:
        def __init__(self, source_node_group, condition):
            self.source_node_group = source_node_group
            self.condition = condition

    def __init__(self):
        self.parent_edges = []
        self.router_node = None

    def has_loose_exits(self):
        if self.router_node:
            for exit in self.router_node.get_exits():
                if exit.destination_uuid is None:
                    return True
        else:
            for edge in self.parent_edges:
                if edge.source_node_group.has_loose_exits():
                    return True

    def connect_loose_exits(self, destination_uuid):
        if self.router_node:
            for exit in self.router_node.get_exits():
                if exit.destination_uuid is None:
                    exit.destination_uuid = destination_uuid
        else:
            for edge in self.parent_edges:
                edge.source_node_group.connect_loose_exits(destination_uuid)

    def entry_node():
        raise NotImplementedError("go_to not implemented to link to no_op row.")

    def add_parent_edge(self, source_node_group, condition):
        self.parent_edges.append(NoOpNodeGroup.ParentEdge(source_node_group,condition))
        if self.router_node is not None:
            source_node_group.add_exit(self.router_node.uuid, condition)

    def add_exit(self, destination_uuid, condition):
        if not self.router_node:
            if condition == Condition():
                for edge in self.parent_edges:
                    edge.source_node_group.add_exit(destination_uuid, edge.condition)
                return
            else:
                assert condition.variable
                self.router_node = SwitchRouterNode(condition.variable)
                self.child_node_ref = None
                for edge in self.parent_edges:
                    # Update all the parent exits
                    edge.source_node_group.add_exit(self.router_node.uuid, edge.condition)

        # We now have a router_node
        # TODO: Code duplication here, especially with respect to default values.
        # Same functionality is in RowNodeGroup
        if not condition.value:
            self.router_node.update_default_exit(destination_uuid)
        else:
            self.router_node.add_choice(
                comparison_variable=condition.variable,
                comparison_type=condition.type or 'has_any_word',
                comparison_arguments=[condition.value],
                category_name=condition.name,
                destination_uuid=destination_uuid,
                is_default=False
            )

    def add_nodes_to_flow(self, flow_container):
        if self.router_node is not None:
            flow_container.add_node(self.router_node)


class RowNodeGroup:
    # Group of nodes representing a row in the sheet.
    # RowNodeGroups have a single exit node
    # (which may have multiple conditional exits)

    def __init__(self, node, row_type):
        '''node: first node in the group'''
        self.nodes = [node]
        self.row_type = row_type

    def is_empty(self):
        # Constructor assumes a node
        return False

    def entry_node(self):
        return self.nodes[0]

    def add_nodes_to_flow(self, flow_container):
        for node in self.nodes:
            flow_container.add_node(node)

    def has_loose_exits(self):
        # A loose exit is a default exit (i.e. exit of a router-less node,
        # or exit connected to the default router case) which is not
        # connected to any further node.
        for exit in self.nodes[-1].get_exits():
            if exit.destination_uuid is None:
                return True
        return False

    def connect_loose_exits(self, destination_uuid):
        for exit in self.nodes[-1].get_exits():
            if exit.destination_uuid is None:
                exit.destination_uuid = destination_uuid

    def add_exit(self, destination_uuid, condition):
        exit_node = self.nodes[-1]
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
                self.has_loose_exit = False
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
            return

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


class FlowParser:

    def __init__(self, rapidpro_container, flow_name, table=None, flow_uuid=None, context=None, sheet_parser=None, content_index_parser=None):
        '''
        rapidpro_container: The parent RapidProContainer to contain the flow generated by this parser.
        flow_name: Name to be given to the flow.
        table: tablib.Dataset: The sheet rows generating the flow;
            either table or sheet_parser must be provided
        flow_uuid: UUID to be given to the flow.
        context: Context to be used when instantiating templates in the flow.
        sheet_parser: SheetParser to be used to generate the flow;
            note that a SheetParser contains a table by iself, and if this argument is provided,
            the table argument is ignored.
        content_index_parser: Required if there are insert_as_block rows.
        '''

        self.rapidpro_container = rapidpro_container
        self.flow_name = flow_name
        self.flow_uuid = flow_uuid
        self.context = context or {}
        if sheet_parser:
            self.sheet_parser = sheet_parser
        else:
            assert table is not None
            row_parser = RowParser(FlowRowModel, CellParser())
            self.sheet_parser = SheetParser(row_parser, table, self.context)
        self.node_group_stack = [NodeGroup()]
        self.row_id_to_nodegroup = defaultdict()
        self.node_name_to_node_map = defaultdict()
        self.content_index_parser = content_index_parser

    def current_node_group(self):
        # New stuff that's created is always added to the current NodeGroup,
        # i.e. the one at the top of the stack.
        return self.node_group_stack[-1]

    def most_recent_node_group(self):
        # None is returned if no row has been processed yet.
        for stack_entry in reversed(self.node_group_stack):
            if not stack_entry.is_empty():
                return stack_entry.last_node_group()
        return None

    def append_node_group(self, new_node_group, row_id):
        self.current_node_group().add_node_group(new_node_group)
        if row_id:
            self.row_id_to_nodegroup[row_id] = new_node_group

    def parse_as_block(self):
        self._parse_block()
        return self.current_node_group()

    def parse(self):
        self._parse_block()
        flow_container = self._compile_flow()
        self.rapidpro_container.add_flow(flow_container)
        return flow_container

    def _parse_block(self, depth=0, block_type='root_block', omit_content=False):
        row = self.sheet_parser.parse_next_row()
        while not self._is_end_of_block(block_type, row):
            if omit_content or not row.include_if:
                if row.type == 'begin_for':
                    self._parse_block(depth+1, 'for', omit_content=True)
                elif row.type == 'begin_block':
                    self._parse_block(depth+1, 'block', omit_content=True)
            else:
                if row.type == 'begin_for':
                    self.sheet_parser.create_bookmark(str(depth))
                    new_node_group = NodeGroup()
                    self.node_group_stack.append(new_node_group)
                    # Interpret the row like a no-op to get the edges
                    if not row.is_starting_row():
                        self._parse_noop_row(row, store_row_id=False)
                    for entry in row.mainarg_iterlist:
                        self.sheet_parser.go_to_bookmark(str(depth))
                        self.sheet_parser.add_to_context(row.loop_variable, entry)
                        self._parse_block(depth+1, 'for')
                    self.node_group_stack.pop()
                    self.append_node_group(new_node_group, row.row_id)
                    self.sheet_parser.remove_from_context(row.loop_variable)
                    self.sheet_parser.remove_bookmark(str(depth))
                elif row.type == 'begin_block':
                    new_node_group = NodeGroup()
                    self.node_group_stack.append(new_node_group)
                    # Interpret the row like a no-op to get the edges
                    if not row.is_starting_row():
                        self._parse_noop_row(row, store_row_id=False)
                    self._parse_block(depth+1, 'block')
                    self.node_group_stack.pop()
                    self.append_node_group(new_node_group, row.row_id)
                else:
                    self._parse_row(row)
            row = self.sheet_parser.parse_next_row()

    def _is_end_of_block(self, block_type, row):
        block_end_map = {
            'end_for' : 'for',
            'end_block' : 'block',
        }
        if row is None:
            if block_type == 'root_block':
                return True
            else:
                raise ValueError('Sheet has unterminated block.')
        elif row.type in block_end_map:
            if block_end_map[row.type] == block_type:
                return True
            else:
                raise ValueError(f'Wrong block terminator "{row.type}" found for block of type {block_type}.')
        return False

    def _parse_insert_as_block_row(self, row):
        if self.content_index_parser is None:
            raise ValueError('insert_as_block only works if FlowParser has a ContentIndexParser')
        node_group = self.content_index_parser.get_node_group(row.mainarg_flow_name, row.data_sheet, row.data_row_id)
        for edge in row.edges:
            self._add_row_edge(edge, node_group.entry_node().uuid)
        self.append_node_group(node_group, row.row_id)
        if row.row_id:
            self.row_id_to_nodegroup[row.row_id] = node_group

    def _get_row_action(self, row):
        attachment_types = [row.image, row.audio, row.video]
        if row.type == 'send_message':
            send_message_action = SendMessageAction(text=row.mainarg_message_text)
            for attachment in [row.image, row.audio, row.video]:
                if attachment:
                    # TODO: Add depending on prefix.
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

    def _get_row_node(self, row):
        if row.type in ['add_to_group', 'remove_from_group', 'split_by_group'] and row.obj_id:
            self.rapidpro_container.record_group_uuid(row.mainarg_groups[0], row.obj_id)

        # TODO: Consider whether to put the functionality of getting
        # a node/action from a row should go into the Node/Action model,
        # considering that the reverse naturally is there as well.
        node_uuid = row.node_uuid or None
        if row.ui_position:
            ui_pos = [int(coord) for coord in row.ui_position]  # List[str] -> List[int]
            assert len(ui_pos) == 2
        else:
            ui_pos = None
        if row.type in ['send_message', 'save_value', 'add_to_group', 'remove_from_group', 'save_flow_result']:
            node = BasicNode(uuid=node_uuid, ui_pos=ui_pos)
            node.update_default_exit(None)
            return node
        elif row.type in ['start_new_flow']:
            if row.obj_id:
                self.rapidpro_container.record_flow_uuid(row.mainarg_flow_name, row.obj_id)
            return EnterFlowNode(row.mainarg_flow_name, uuid=node_uuid, ui_pos=ui_pos)
        elif row.type in ['wait_for_response']:
            if row.no_response:
                return SwitchRouterNode('@input.text', result_name=row.save_name, wait_timeout=int(row.no_response), uuid=node_uuid, ui_pos=ui_pos)
            else:
                return SwitchRouterNode('@input.text', result_name=row.save_name, wait_timeout=0, uuid=node_uuid, ui_pos=ui_pos)
        elif row.type in ['split_by_value']:
            return SwitchRouterNode(row.mainarg_expression, result_name=row.save_name, wait_timeout=None, uuid=node_uuid, ui_pos=ui_pos)
        elif row.type in ['split_by_group']:
            return SwitchRouterNode('@contact.groups', result_name=row.save_name, wait_timeout=None, uuid=node_uuid, ui_pos=ui_pos)
        elif row.type in ['split_random']:
            return RandomRouterNode(result_name=row.save_name, uuid=node_uuid, ui_pos=ui_pos)
        else:
            return BasicNode(uuid=node_uuid, ui_pos=ui_pos)

    def _get_node_name(self, row):
        return row.node_uuid or row.node_name

    def _get_node_group_from_edge(self, edge):
        if edge.from_ == 'start':
            return None
        elif edge.from_:
            if edge.from_ not in self.row_id_to_nodegroup:
                raise ValueError(f'Edge from row_id "{edge.from_}" which does not exist.')
            return self.row_id_to_nodegroup[edge.from_]
        else:
            return self.most_recent_node_group()
            # if from_node_group is None:
            #     # Doesn't come from 'start', but is the first ACTUAL
            #     # node in the flow (the first row could be e.g. begin_for
            #     # or begin_block, which doesn't generate a node)
            #     # Because we have a dummy node group for begin_for/begin_block,
            #     # we actually know this is the first node, and we can issue a warning here:
            #     # 'First node must have edge from "start"'
            #     return None        

    def _add_row_edge(self, edge, destination_uuid):
        from_node_group = self._get_node_group_from_edge(edge)
        if from_node_group is not None:
            from_node_group.add_exit(destination_uuid, edge.condition)

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

    def _parse_noop_row(self, row, store_row_id=True):
        new_node = NoOpNodeGroup()
        for edge in row.edges:
            source_node_group = self._get_node_group_from_edge(edge)
            if source_node_group is not None:
                new_node.add_parent_edge(source_node_group, edge.condition)
        self.append_node_group(new_node, row.row_id if store_row_id else '')

    def _parse_row(self, row):
        if not row.include_if:
            return

        if row.type in ['hard_exit', 'loose_exit']:
            destination_uuid = 'HARD_EXIT' if row.type == 'hard_exit' else None
            for edge in row.edges:
                self._add_row_edge(edge, destination_uuid)
            return

        if row.type == 'go_to':
            self._parse_goto_row(row)
            return

        if row.type == 'no_op':
            self._parse_noop_row(row)
            return

        if row.type == 'insert_as_block':
            self._parse_insert_as_block_row(row)
            return

        row_action = self._get_row_action(row)
        node_name = self._get_node_name(row)
        existing_node = self.node_name_to_node_map.get(node_name)

        if node_name and existing_node and row_action:
            # If we want to add an action to an existing node of a given name,
            # there must be exactly one unconditional edge, and the
            # from_ row_id has to match.
            if len(row.edges) == 1 and row.edges[0].condition == Condition():
                # Get the group that this row is linked to.
                if row.edges[0].from_:
                    predecessor_group = self.row_id_to_nodegroup.get(row.edges[0].from_)
                else:
                    predecessor_group = self.most_recent_node_group()
                if predecessor_group.entry_node() == existing_node:
                    existing_node.add_action(row_action)
                    if row.row_id:
                        self.row_id_to_nodegroup[row.row_id] = self.row_id_to_nodegroup[row.edges[0].from_]
                    return
                else:
                    raise ValueError(f'To merge rows using node name {node_name} into a single node, edge must come from a rode with node name {node_name}.')
            else:
                raise ValueError(f'To merge rows using node name {node_name} into a single node, there must be exactly one unconditional incoming edge.')

        new_node = self._get_row_node(row)
        if row_action:
            new_node.add_action(row_action)

        for edge in row.edges:
            self._add_row_edge(edge, new_node.uuid)

        new_node_group = RowNodeGroup(new_node, row.type)
        self.append_node_group(new_node_group, row.row_id)
        self.node_name_to_node_map[self._get_node_name(row)] = new_node

    def _compile_flow(self):
        '''
        Referenced groups or other flows may have a UUID which is None.
        Add the flow to a RapidProContainer and run update_global_uuids
        to fill in these missing UUIDs in a consistent way.
        '''

        # Caveat/TODO: Need to ensure starting node comes first.
        flow_container = FlowContainer(flow_name=self.flow_name, uuid=self.flow_uuid)
        assert len(self.node_group_stack) == 1
        self.current_node_group().add_nodes_to_flow(flow_container)
        return flow_container
