from rapidpro.models.actions import Action, EnterFlowAction
from rapidpro.models.common import Exit

from rapidpro.models.routers import SwitchRouter, RandomRouter
from rapidpro.utils import generate_new_uuid


# In practice, nodes have either a router or a non-zero amount of actions.
#     (I don't know if this is a technical restriction, or convention to make
#     visualization in the UI work.)
# The only exception is enter_flow, which has both.
#     (a flow can be completed or expire, hence the router)
# A node with neither is meaningless, so our output shouldn't have such nodes


# I believe that it is true that whenever we create a node,
# we know what type of node it is.
# Thus it is sensible to implement nodes via classes
# Class tree (suggestion)
# GenericNode (allows for actions)
#   SwitchRouterNode
#     EnterFlowNode
#     WebhookNode
#   RandomRouterNode
# possibly more: dedicated subclasses for any kind of node where
# there is extra complexity that goes beyond the Action object.
#   wait_for_response is a potential instance of that


class BaseNode:
    def __init__(self, uuid=None, destination_uuid=None, default_exit=None, actions=None):
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

    def from_dict(data, ui_data=None):
        if "router" in data:
            if data["router"]["type"] == "random":
                return RandomRouterNode.from_dict(data, ui_data)
            elif data["router"]["type"] == "switch":
                if data["router"]["operand"] == "@child.run.status":
                    return EnterFlowNode.from_dict(data, ui_data)
                else:
                    return SwitchRouterNode.from_dict(data, ui_data)
            else:
                raise ValueError("Node contains router of invalid type")
        else:
            return BasicNode.from_dict(data, ui_data)

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

    def _get_exits(self):
        return self.exits

    def render(self):
        self.validate()
        # recursively render the elements of the node
        fields = {
            'uuid': self.uuid,
            'actions': [action.render() for action in self.actions],
            'exits': [exit.render() for exit in self._get_exits()],
        }
        if self.router is not None:
            fields.update({
                'router': self.router.render(),
            })
        return fields


class BasicNode(BaseNode):
    # A basic node can accomodate actions and a very basic exit

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        if len(exits) != 1:
            raise ValueError("Basic node must have exactly one exit")
        actions = [Action.from_dict(action) for action in data["actions"]]
        return BasicNode(uuid=data["uuid"], default_exit=exits[0], actions=actions)

    def _add_exit(self, exit):
        raise NotImplementedError

    def validate(self):
        if not self.has_basic_exit:
            raise ValueError('has_basic_exit must be True for BasicNode')

        if not self.default_exit:
            raise ValueError('default_exit must be set for BasicNode')


class SwitchRouterNode(BaseNode):

    def __init__(self, operand=None, result_name=None, wait_timeout=None, uuid=None, router=None):
        # TODO: Support proper wait, not just true/false
        '''
        Either an operand or a router need to be provided
        '''
        super().__init__(uuid)
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

    def add_choice(self, *args, **kwargs):
        self.router.add_choice(*args, **kwargs)

    def update_default_exit(self, destination_uuid):
        self.router.update_default_category(destination_uuid)

    def record_global_uuids(self, uuid_dict):
        super().record_global_uuids(uuid_dict)
        self.router.record_global_uuids(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        super().assign_global_uuids(uuid_dict)
        self.router.assign_global_uuids(uuid_dict)

    def validate(self):
        if self.has_basic_exit:
            raise ValueError('Basic exits are not supported in SwitchRouterNode')
        self.router.validate()

    def _get_exits(self):
        return self.router.get_exits()


class RandomRouterNode(BaseNode):

    def __init__(self, result_name=None, uuid=None, router=None):
        super().__init__(uuid)
        if router:
            self.router = router
        else:
            self.router = RandomRouter(result_name)
        self.has_basic_exit = False

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        router = RandomRouter.from_dict(data["router"], exits)
        return RandomRouterNode(uuid=data["uuid"], router=router)

    def add_choice(self, **kwargs):
        self.router.add_choice(**kwargs)

    def validate(self):
        if self.has_basic_exit:
            raise ValueError('Default exits are not supported in SwitchRouterNode')

        self.router.validate()

    def _get_exits(self):
        return self.router.get_exits()


class EnterFlowNode(BaseNode):
    def __init__(self, flow_name=None, complete_destination_uuid=None, expired_destination_uuid=None, uuid=None, router=None, action=None):
        '''
        Either an action or a flow_name have to be provided.
        '''
        super().__init__(uuid)

        if action:
            if action.type != "enter_flow":
                raise ValueError("Action for EnterFlowNode must be of type enter_flow")
            self.add_action(action)
        else:
            if not flow_name:
                raise ValueError("Either an action or a flow_name have to be provided.")
            self.add_action(EnterFlowAction(flow_name))

        if router:
            self.router = router
        else:
            self.router = SwitchRouter(operand='@child.run.status', result_name=None, wait_timeout=None)
            self.router.default_category.update_name('Expired')

            self.add_choice(comparison_variable='@child.run.status', comparison_type='has_only_text',
                            comparison_arguments=['completed'], category_name='Complete',
                            destination_uuid=complete_destination_uuid)
            self.add_choice(comparison_variable='@child.run.status', comparison_type='has_only_text',
                            comparison_arguments=['expired'], category_name='Expired',
                            destination_uuid=expired_destination_uuid, is_default=True)
            # Suppress the warning about overwriting default category
            self.router.has_explicit_default_category = False

    def from_dict(data, ui_data=None):
        exits = [Exit.from_dict(exit_data) for exit_data in data["exits"]]
        router = SwitchRouter.from_dict(data["router"], exits)
        actions = [Action.from_dict(action) for action in data["actions"]]
        if len(actions) != 1:
            raise ValueError("EnterFlowNode node must have exactly one action")
        return EnterFlowNode(uuid=data["uuid"], router=router, action=actions[0])

    def add_choice(self, **kwargs):
        # TODO: validate the input
        self.router.add_choice(**kwargs)

    def update_default_exit(self, destination_uuid):
        raise ValueError("EnterFlowNode does not support default exits.")

    def update_completed_exit(self, destination_uuid):
        category = self.router._get_category_or_none('Complete')
        category.update_destination_uuid(destination_uuid)

    def update_expired_exit(self, destination_uuid):
        self.router.update_default_category(destination_uuid)

    def validate(self):
        pass

    def _get_exits(self):
        return self.router.get_exits()

