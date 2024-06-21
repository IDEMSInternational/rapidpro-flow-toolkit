import re
from abc import ABC, abstractmethod

from rpft.parsers.creation.flowrowmodel import (
    Edge,
    FlowRowModel,
)
from rpft.rapidpro.models.actions import (
    Action,
    CallWebhookAction,
    EnterFlowAction,
    TransferAirtimeAction,
)
from rpft.rapidpro.models.common import Exit, generate_field_key, mangle_string
from rpft.rapidpro.models.routers import RandomRouter, SwitchRouter
from rpft.rapidpro.utils import generate_new_uuid

# TODO: EnterFlowNode and WebhookNode are currently children of BaseNode.
# Ideal class tree of nodes:
# BaseNode
#   BasicNode (allows for actions, only has one exit [no router])
#   SwitchRouterNode (has router and multiple exits; should support actions for its
#   subclasses.)
#     EnterFlowNode
#     WebhookNode
#   RandomRouterNode
# TODO: Make BaseNode an abstract class


class BaseNode(ABC):
    def __init__(
        self,
        uuid=None,
        destination_uuid=None,
        default_exit=None,
        actions=None,
        ui_pos=None,
    ):
        self.uuid = uuid or generate_new_uuid()
        self.actions = actions or []
        self.router = None

        # has_basic_exit denotes if the node should have only one exit
        # This generally occurs in cases where there is no router
        # if has_basic_exit is True, we will render a (very basic) exit which
        # points to default_exit_uuid
        self.has_basic_exit = True
        if default_exit:
            self.default_exit = default_exit
        else:
            self.default_exit = Exit(destination_uuid=destination_uuid or None)
        self.exits = [self.default_exit]
        self.ui_pos = ui_pos

    def from_dict(data, ui_data=None):
        if "router" in data:
            if data["router"]["type"] == "random":
                return RandomRouterNode.from_dict(data, ui_data)
            elif data["router"]["type"] == "switch":
                if data["actions"]:
                    if data["actions"][0]["type"] == "enter_flow":
                        return EnterFlowNode.from_dict(data, ui_data)
                    elif data["actions"][0]["type"] == "call_webhook":
                        return CallWebhookNode.from_dict(data, ui_data)
                    elif data["actions"][0]["type"] == "transfer_airtime":
                        return TransferAirtimeNode.from_dict(data, ui_data)
                    else:
                        raise ValueError("Node contains action of invalid type")
                else:
                    return SwitchRouterNode.from_dict(data, ui_data)
            else:
                raise ValueError("Node contains router of invalid type")
        else:
            return BasicNode.from_dict(data, ui_data)

    def add_ui_from_dict(self, ui_dict):
        if self.uuid in ui_dict:
            pos_dict = ui_dict[self.uuid]["position"]
            self.ui_pos = (pos_dict["left"], pos_dict["top"])
        else:
            self.ui_pos = None

    def update_default_exit(self, destination_uuid):
        # TODO: Think of any caveats to storing a node rather than a UUID
        self.default_exit = Exit(destination_uuid=destination_uuid)
        self.exits = [self.default_exit]

    def _add_exit(self, exit):
        self.exits.append(exit)

    def add_action(self, action):
        self.actions.append(action)

    def record_global_uuids(self, uuid_dict):
        for action in self.actions:
            action.record_global_uuids(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        for action in self.actions:
            action.assign_global_uuids(uuid_dict)

    def add_choice(self):
        raise NotImplementedError

    def validate(self):
        raise NotImplementedError

    def get_last_action(self):
        try:
            return self.actions[-1]
        except IndexError:
            return None

    def get_exits(self):
        return self.exits

    def render(self):
        self.validate()
        # recursively render the elements of the node
        fields = {
            "uuid": self.uuid,
            "exits": [exit.render() for exit in self.get_exits()],
        }
        if self.actions is not None:
            fields["actions"] = [action.render() for action in self.actions]
        if self.router is not None:
            fields.update(
                {
                    "router": self.router.render(),
                }
            )
        return fields

    def render_ui(self):
        if self.ui_pos:
            return {
                "position": {
                    "left": self.ui_pos[0],
                    "top": self.ui_pos[1],
                },
                "type": "execute_actions",
            }
        else:
            return None

    def clear_row_model(self):
        self.row_models = []

    def get_row_models(self):
        return self.row_models

    def prepend_edge_to_row_models(self, edge):
        self.row_models[0].edges.insert(0, edge)

    @abstractmethod
    def short_name(self):
        pass

    @abstractmethod
    def initiate_row_models(self, node_row_id, parent_edge, **kwargs):
        self.row_models = []
        if self.actions:
            for i, action in enumerate(self.actions):
                action_fields = action.get_row_model_fields()
                row_id = f"{node_row_id}.{i}" if i else node_row_id
                row_model = FlowRowModel(
                    row_id=row_id,
                    edges=[parent_edge],
                    node_uuid=self.uuid,
                    ui_position=self.ui_pos or [],
                    **action_fields,
                )
                self.row_models.append(row_model)
                parent_edge = Edge(from_=row_id)
        else:
            self.row_models = [
                FlowRowModel(
                    row_id=node_row_id,
                    edges=[parent_edge],
                    node_uuid=self.uuid,
                    ui_position=self.ui_pos or [],
                    **kwargs,
                )
            ]

    @abstractmethod
    def get_exit_edge_pairs(self):
        pass


class BasicNode(BaseNode):
    # A basic node can accomodate actions and a single (default) exit

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        if len(exits) != 1:
            raise ValueError("Basic node must have exactly one exit")
        actions = [Action.from_dict(action) for action in data["actions"]]
        return BasicNode(uuid=data["uuid"], default_exit=exits[0], actions=actions)

    def _add_exit(self, exit):
        raise NotImplementedError

    def short_name(self):
        return self.actions[0].short_name()

    def validate(self):
        if not self.has_basic_exit:
            raise ValueError("has_basic_exit must be True for BasicNode")

        if not self.default_exit:
            raise ValueError("default_exit must be set for BasicNode")

    def initiate_row_models(self, current_row_id, parent_edge):
        super().initiate_row_models(current_row_id, parent_edge)

    def get_exit_edge_pairs(self):
        return [(self.default_exit, Edge(from_=self.row_models[-1].row_id))]


class RouterNode(BaseNode, ABC):
    def add_choice(self, *args, **kwargs):
        # Subclasses may choose to validate the input
        self.router.add_choice(*args, **kwargs)

    def update_default_exit(self, destination_uuid):
        self.router.update_default_category(destination_uuid)

    def record_global_uuids(self, uuid_dict):
        super().record_global_uuids(uuid_dict)
        self.router.record_global_uuids(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        super().assign_global_uuids(uuid_dict)
        self.router.assign_global_uuids(uuid_dict)

    def get_exits(self):
        return self.router.get_exits()

    def get_exit_edge_pairs(self):
        return self.router.get_exit_edge_pairs(self.row_models[-1].row_id)


class SwitchRouterNode(RouterNode):
    def __init__(
        self,
        operand=None,
        result_name=None,
        wait_timeout=None,
        uuid=None,
        router=None,
        ui_pos=None,
    ):
        """
        Either an operand or a router need to be provided
        """
        super().__init__(uuid, ui_pos=ui_pos)
        if router:
            self.router = router
        else:
            if not operand:
                raise ValueError("Either an operand or a router need to be provided")
            self.router = SwitchRouter(operand, result_name, wait_timeout)
        self.has_basic_exit = False

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        router = SwitchRouter.from_dict(data["router"], exits)
        return SwitchRouterNode(uuid=data["uuid"], router=router)

    def short_name(self):
        short_value = mangle_string(self.router.result_name or self.router.operand)
        if self.router.wait_timeout:
            return f"wait_for.{short_value}"
        else:
            return f"switch.{short_value}"

    def update_no_response_exit(self, destination_uuid):
        self.router.update_no_response_category(destination_uuid)

    def has_wait(self):
        return self.router.has_wait()

    def has_positive_wait(self):
        return self.router.has_positive_wait()

    def validate(self):
        if self.has_basic_exit:
            raise ValueError("Basic exits are not supported in SwitchRouterNode")
        self.router.validate()

    def render_ui(self):
        ui_entry = super().render_ui()
        if not ui_entry:
            return None
        matches_scheme = re.match(
            r'@\(default\(urn_parts\(urns\.([a-z]+)\)\.path,\s+""\)\)',
            self.router.operand,
        )
        # TODO: for results/fields, the title cannot be inferred from the id alone.
        # We should therefore get it using a dict of fields.
        if self.has_wait():
            ui_entry["type"] = "wait_for_response"
            ui_entry["config"] = {"cases": {}}
        elif self.router.operand == "@contact.groups":
            ui_entry["type"] = "split_by_groups"
            ui_entry["config"] = {"cases": {}}
        elif self.router.operand == "@(urn_parts(contact.urn).scheme)":
            ui_entry["type"] = "split_by_scheme"
            ui_entry["config"] = {"cases": {}}
        elif (
            self.router.operand.startswith("@contact.")
            or self.router.operand.startswith("@fields.")
            or matches_scheme
        ):
            if matches_scheme:
                field_id = matches_scheme.group(1)
                field_type = "scheme"
                field_title = field_id.title()
                # TODO: Technically, the field name is custom here.
                # For example, if the id is 'mailto', the name is 'Email Address'
                # As the name is not very important, we ignore this for now.
            else:
                field_id = re.sub("(@contact.)|(@fields.)", "", self.router.operand)
                field_title = field_id
                if self.router.operand.startswith("@contact.") and field_id in [
                    "name",
                    "language",
                    "channel",
                ]:
                    field_type = "property"
                    field_title = field_id.title()
                else:
                    field_type = "field"
            ui_entry["type"] = "split_by_contact_field"
            ui_entry["config"] = {
                "cases": {},
                "operand": {
                    "id": field_id,
                    "type": field_type,  # TODO: can this take other values?
                    "name": field_title,
                },
            }
        elif self.router.operand.startswith("@results."):
            result_id = field_id = re.sub("(@results.)", "", self.router.operand)
            result_title = result_id
            ui_entry["type"] = "split_by_run_result"
            ui_entry["config"] = {
                "cases": {},
                "operand": {
                    "id": result_id,
                    "type": "result",  # TODO: can this take other values?
                    "name": result_title,  # This is a heuristic.
                },
            }
        else:
            ui_entry["type"] = "split_by_expression"
            ui_entry["config"] = {"cases": {}}
        return ui_entry

    def initiate_row_models(self, current_row_id, parent_edge):
        if self.has_wait():
            super().initiate_row_models(
                current_row_id,
                parent_edge,
                type="wait_for_response",
                save_name=self.router.result_name or "",
                no_response=self.router.wait_timeout or "",
            )
        elif self.router.operand == "@contact.groups":
            # TODO: What about multiple groups?
            # TODO: groups in cases should be implemented differently.
            super().initiate_row_models(
                current_row_id,
                parent_edge,
                type="split_by_group",
                mainarg_groups=[self.router.cases[0].arguments[1]],
                obj_id=self.router.cases[0].arguments[0]
                or "",  # obj_id is not yet a list.
            )
        else:
            super().initiate_row_models(
                current_row_id,
                parent_edge,
                type="split_by_value",
                mainarg_expression=self.router.operand,
            )


class RandomRouterNode(RouterNode):
    def __init__(self, result_name=None, uuid=None, router=None, ui_pos=None):
        super().__init__(uuid, ui_pos=ui_pos)
        if router:
            self.router = router
        else:
            self.router = RandomRouter(result_name)
        self.has_basic_exit = False

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        router = RandomRouter.from_dict(data["router"], exits)
        return RandomRouterNode(uuid=data["uuid"], router=router)

    def update_default_exit(self, destination_uuid):
        raise ValueError("RandomRouterNode does not support default exits.")

    def short_name(self):
        if self.router.result_name:
            short_value = mangle_string(self.router.result_name)
            return f"random.{short_value}"
        else:
            return "random"

    def validate(self):
        if self.has_basic_exit:
            raise ValueError("Default exits are not supported in RandomRouterNode")

        self.router.validate()

    def render_ui(self):
        ui_entry = super().render_ui()
        if not ui_entry:
            return None
        ui_entry["type"] = "split_by_random"
        ui_entry["config"] = None
        return ui_entry

    def initiate_row_models(self, current_row_id, parent_edge):
        super().initiate_row_models(
            current_row_id,
            parent_edge,
            type="split_random",
        )


class EnterFlowNode(RouterNode):
    def __init__(
        self,
        flow_name=None,
        flow_uuid=None,
        complete_destination_uuid=None,
        expired_destination_uuid=None,
        uuid=None,
        router=None,
        action=None,
        ui_pos=None,
    ):
        """
        Either an action or a flow_name have to be provided.
        """
        super().__init__(uuid, ui_pos=ui_pos)

        if action:
            if action.type != "enter_flow":
                raise ValueError("Action for EnterFlowNode must be of type enter_flow")
            self.add_action(action)
        else:
            if not flow_name:
                raise ValueError("Either an action or a flow_name have to be provided.")
            self.add_action(EnterFlowAction(flow_name, flow_uuid))

        if router:
            self.router = router
        else:
            self.router = SwitchRouter(
                operand="@child.run.status", result_name=None, wait_timeout=None
            )
            self.router.default_category.update_name("Expired")

            self.add_choice(
                comparison_variable="@child.run.status",
                comparison_type="has_only_text",
                comparison_arguments=["completed"],
                category_name="Complete",
                destination_uuid=complete_destination_uuid,
            )
            self.add_choice(
                comparison_variable="@child.run.status",
                comparison_type="has_only_text",
                comparison_arguments=["expired"],
                category_name="Expired",
                destination_uuid=expired_destination_uuid,
                is_default=True,
            )
            # Suppress the warning about overwriting default category
            self.router.has_explicit_default_category = False

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        router = SwitchRouter.from_dict(data["router"], exits)
        actions = [Action.from_dict(action) for action in data["actions"]]
        if len(actions) != 1:
            raise ValueError("EnterFlowNode node must have exactly one action")
        return EnterFlowNode(uuid=data["uuid"], router=router, action=actions[0])

    def short_name(self):
        return self.actions[0].short_name()

    def update_default_exit(self, destination_uuid):
        raise ValueError("EnterFlowNode does not support default exits.")

    def update_completed_exit(self, destination_uuid):
        category = self.router._get_category_or_none("Complete")
        category.update_destination_uuid(destination_uuid)

    def update_expired_exit(self, destination_uuid):
        self.router.update_default_category(destination_uuid)

    def validate(self):
        pass

    def render_ui(self):
        ui_entry = super().render_ui()
        if not ui_entry:
            return None
        ui_entry["type"] = "split_by_subflow"
        ui_entry["config"] = {}
        return ui_entry

    def initiate_row_models(self, current_row_id, parent_edge):
        # Note: We want to call the method of the BaseNode class here.
        # If we refactor this to be a child of SwitchRouterNode, careful here!
        super().initiate_row_models(current_row_id, parent_edge)


class CallWebhookNode(RouterNode):
    def __init__(
        self,
        result_name=None,
        url=None,
        method=None,
        body="",
        headers=None,
        success_destination_uuid=None,
        failure_destination_uuid=None,
        uuid=None,
        router=None,
        action=None,
        ui_pos=None,
    ):
        """
        Either an action or a flow_name have to be provided.
        """
        super().__init__(uuid, ui_pos=ui_pos)

        method = method or "POST"
        http_methods = ["CONNECT", "DELETE", "GET", "HEAD", "OPTIONS", "POST", "PUT"]
        if method not in http_methods:
            raise ValueError("Method for WebhookNode must a valid HTTP method")
        headers = headers or {}
        assert type(headers) is dict

        if action:
            if action.type != "call_webhook":
                raise ValueError("Action for WebhookNode must be of type call_webhook")
            self.add_action(action)
        else:
            if not url or not result_name:
                raise ValueError(
                    "Either an action or a url/result_name have to be provided."
                )
            action = CallWebhookAction(
                result_name=result_name,
                url=url,
                method=method,
                body=body,
                headers=headers,
            )
            self.add_action(action)

        if router:
            self.router = router
        else:
            result_field = generate_field_key(result_name)
            self.router = SwitchRouter(
                operand=f"@results.{result_field}.category",
                result_name=None,
                wait_timeout=None,
            )
            self.router.default_category.update_name("Failure")

            self.add_choice(
                comparison_variable=f"@results.{result_field}.category",
                comparison_type="has_only_text",
                comparison_arguments=["Success"],
                category_name="Success",
                destination_uuid=success_destination_uuid,
            )
            self.router.update_default_category(failure_destination_uuid, "Failure")
            # Suppress the warning about overwriting default category
            self.router.has_explicit_default_category = False

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        router = SwitchRouter.from_dict(data["router"], exits)
        actions = [Action.from_dict(action) for action in data["actions"]]
        if len(actions) != 1:
            raise ValueError("WebhookNode node must have exactly one action")
        return CallWebhookNode(uuid=data["uuid"], router=router, action=actions[0])

    def update_success_exit(self, destination_uuid):
        category = self.router._get_category_or_none("Success")
        category.update_destination_uuid(destination_uuid)

    def update_failure_exit(self, destination_uuid):
        self.update_default_exit(destination_uuid)

    def short_name(self):
        short_value = mangle_string(self.router.result_name or self.actions[0].url)
        return f"webhook.{short_value}"

    def validate(self):
        pass

    def render_ui(self):
        ui_entry = super().render_ui()
        if not ui_entry:
            return None
        ui_entry["type"] = "split_by_webhook"
        ui_entry["config"] = {}
        return ui_entry

    def initiate_row_models(self, current_row_id, parent_edge):
        super().initiate_row_models(current_row_id, parent_edge)


class TransferAirtimeNode(RouterNode):
    def __init__(
        self,
        amounts=None,
        result_name=None,
        success_destination_uuid=None,
        failure_destination_uuid=None,
        uuid=None,
        router=None,
        action=None,
        ui_pos=None,
    ):
        """
        Either an action or a flow_name have to be provided.
        """
        super().__init__(uuid, ui_pos=ui_pos)

        if action:
            if action.type != "transfer_airtime":
                raise ValueError(
                    "Action for TransferAirtimeNode must be of type transfer_airtime"
                )
            self.add_action(action)
        else:
            if not amounts or not result_name:
                raise ValueError(
                    "Either an action or a amounts/result_name have to be provided."
                )
            assert type(amounts) is dict
            action = TransferAirtimeAction(
                amounts=amounts,
                result_name=result_name,
            )
            self.add_action(action)

        if router:
            self.router = router
        else:
            result_field = generate_field_key(result_name)
            self.router = SwitchRouter(
                operand=f"@results.{result_field}",
            )
            self.router.default_category.update_name("Failure")

            self.add_choice(
                comparison_variable=f"@results.{result_field}",
                comparison_type="has_category",
                comparison_arguments=["Success"],
                category_name="Success",
                destination_uuid=success_destination_uuid,
            )
            self.router.update_default_category(failure_destination_uuid, "Failure")
            # Suppress the warning about overwriting default category
            self.router.has_explicit_default_category = False

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        router = SwitchRouter.from_dict(data["router"], exits)
        actions = [Action.from_dict(action) for action in data["actions"]]
        if len(actions) != 1:
            raise ValueError("TransferAirtimeNode node must have exactly one action")
        return TransferAirtimeNode(uuid=data["uuid"], router=router, action=actions[0])

    def update_success_exit(self, destination_uuid):
        category = self.router._get_category_or_none("Success")
        category.update_destination_uuid(destination_uuid)

    def update_failure_exit(self, destination_uuid):
        self.update_default_exit(destination_uuid)

    def short_name(self):
        short_value = mangle_string(self.actions[0].result_name)
        return f"airtime.{short_value}"

    def validate(self):
        pass

    def render_ui(self):
        ui_entry = super().render_ui()
        if not ui_entry:
            return None
        ui_entry["type"] = "split_by_airtime"
        ui_entry["config"] = {}
        return ui_entry

    def initiate_row_models(self, current_row_id, parent_edge):
        super().initiate_row_models(current_row_id, parent_edge)
