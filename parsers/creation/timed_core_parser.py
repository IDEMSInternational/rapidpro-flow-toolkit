from rapidpro.models.actions import SendMessageAction, SetContactFieldAction, SetRunResultAction
from rapidpro.models.containers import FlowContainer, RapidProContainer
from rapidpro.models.nodes import BasicNode, SwitchRouterNode, EnterFlowNode
from parsers.common.cellparser import CellParser
from parsers.common.rowparser import RowParser
from parsers.creation.timed_core_models import RowData


class Parser:
    # Note: The output flow invokes existing flows whose names are given
    # here, but whose uuids are not. In these enter-flow nodes, the UUIDs
    # of these referenced flows are set to None.
    # In order to import the output into RapidPro, invoke
    # container.update_global_uuids(...) on the output container,
    # and either explicitly provide a UUIDDict with a map from names to
    # UUIDs, or add the invoked flows to the container before calling
    # update_global_uuids.

    def __init__(self, rows, container=None):
        self.container = container or RapidProContainer()
        row_parser = RowParser(RowData, CellParser())
        self.data_rows = [row_parser.parse_row(row) for row in rows]

    def parse(self):
        for row in self.data_rows:
            self._parse_row(row)

    def _parse_row(self, row):
        flow = FlowContainer(f'{row.flow_name} - Timed intro')

        start_node = BasicNode()
        start_node.add_action(SetRunResultAction(row.result.variable, row.result.value, category=None))
        flow.add_node(start_node)

        enter_toolkit_flow_node = EnterFlowNode("PLH - Internal - Update incomplete toolkits")
        start_node.update_default_exit(enter_toolkit_flow_node.uuid)
        flow.add_node(enter_toolkit_flow_node)

        # TODO: Don't add empty string attachments
        main_message_node = BasicNode()
        for message in row.main_messages:
            if message.text:
                action = SendMessageAction(text=message.text, attachments=[message.attachment])
                main_message_node.add_action(action)
        enter_toolkit_flow_node.update_completed_exit(main_message_node.uuid)
        enter_toolkit_flow_node.update_expired_exit(main_message_node.uuid)
        flow.add_node(main_message_node)

        toolkit_switch_node = SwitchRouterNode('@fields.toolkit')
        main_message_node.update_default_exit(toolkit_switch_node.uuid)
        flow.add_node(toolkit_switch_node)

        already_received_message_node = BasicNode()
        if row.already_received_message.text:
            already_received_message_node.add_action(SendMessageAction(text=row.already_received_message.text, attachments=[row.already_received_message.attachment], quick_replies=['Yes', 'No']))
        toolkit_switch_node.add_choice('@fields.toolkit', 'has_phrase', ['@results.skill'], 'already completed', already_received_message_node.uuid)
        flow.add_node(already_received_message_node)

        learn_more_message_node = BasicNode()
        learn_more_message_node.add_action(SendMessageAction(text="Would you like to learn more about this tip?", quick_replies=['Yes', 'No']))
        toolkit_switch_node.update_default_exit(learn_more_message_node.uuid)
        flow.add_node(learn_more_message_node)

        know_more_input_node = SwitchRouterNode('@input.text', result_name='know_more', wait_for_message=True)
        already_received_message_node.update_default_exit(know_more_input_node.uuid)
        learn_more_message_node.update_default_exit(know_more_input_node.uuid)
        flow.add_node(know_more_input_node)

        no_message_node = BasicNode()
        for message in row.no_messages:
            if message.text:
                action = SendMessageAction(text=message.text, attachments=[message.attachment])
                no_message_node.add_action(action)
        no_message_node.add_action(SetContactFieldAction(field_name='last interaction', value='@(now())'))
        know_more_input_node.add_choice('@input.text', 'has_any_word', ['no n'], 'No', no_message_node.uuid)
        flow.add_node(no_message_node)

        dont_understand_node = BasicNode()
        dont_understand_node.add_action(SendMessageAction(text="Sorry, I don't understand what you mean."))
        dont_understand_node.add_action(SetContactFieldAction(field_name='last interaction', value='@(now())'))
        dont_understand_node.update_default_exit(toolkit_switch_node.uuid)
        know_more_input_node.update_default_exit(dont_understand_node.uuid)
        flow.add_node(dont_understand_node)

        know_mode_yes_node = BasicNode()
        know_mode_yes_node.add_action(SetContactFieldAction(field_name='from theme', value='yes'))
        know_mode_yes_node.add_action(SetContactFieldAction(field_name='last interaction', value='@(now())'))
        know_more_input_node.add_choice('@input.text', 'has_any_word', ['yes y'], 'Yes', know_mode_yes_node.uuid)
        flow.add_node(know_mode_yes_node)

        enter_toolkit_flow_node = EnterFlowNode(row.flow_name)
        know_mode_yes_node.update_default_exit(enter_toolkit_flow_node.uuid)
        flow.add_node(enter_toolkit_flow_node)

        is_busy_node = BasicNode()
        is_busy_node.add_action(SetContactFieldAction(field_name='from theme', value='no'))
        is_busy_node.add_action(SetContactFieldAction(field_name='has expired', value='tip'))
        is_busy_node.add_action(SendMessageAction(text="It looks like you are busy right now. You can always type \"GoBack\" to restart this parenting tip or \"Help\" for other support."))
        enter_toolkit_flow_node.update_expired_exit(is_busy_node.uuid)
        flow.add_node(is_busy_node)

        extra_message_node = BasicNode()
        extra_message_node.add_action(SetContactFieldAction(field_name='from theme', value='no'))
        for message in row.extra_messages:
            if message.text:
                action = SendMessageAction(text=message.text, attachments=[message.attachment])
                extra_message_node.add_action(action)
        enter_toolkit_flow_node.update_completed_exit(extra_message_node.uuid)
        flow.add_node(extra_message_node)

        self.container.add_flow(flow)

    def get_container(self):
        return self.container

