from rapidpro.models.actions import EnterFlowAction
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
    def __init__(self, uuid=None):
        self.uuid = uuid or generate_new_uuid()
        self.actions = []
        self.router = None

        # has_basic_exit denotes if the node should have only one exit
        # This generally occurs in cases where there is no router
        # if has_basic_exit is True, we will render a (very basic) exit which
        # points to default_exit_uuid
        self.has_basic_exit = True
        self.default_exit = Exit(destination_uuid=None)
        self.exits = [self.default_exit]

    def update_default_exit(self, destination_uuid):
        # TODO: Think of any caveats to storing a node rather than a UUID
        self.default_exit = Exit(destination_uuid=destination_uuid)
        self.exits = [self.default_exit]

    def _add_exit(self, exit):
        self.exits.append(exit)

    def add_action(self, action):
        self.actions.append(action)

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

    def _add_exit(self, exit):
        raise NotImplementedError

    def validate(self):
        if not self.has_basic_exit:
            raise ValueError('has_basic_exit must be True for BasicNode')

        if not self.default_exit:
            raise ValueError('default_exit must be set for BasicNode')


class SwitchRouterNode(BaseNode):

    def __init__(self, operand, result_name=None, wait_for_message=False, uuid=None):
        super().__init__(uuid)
        self.router = SwitchRouter(operand, result_name, wait_for_message)
        self.has_basic_exit = False

    def add_choice(self, **kwargs):
        self.router.add_choice(**kwargs)

    def update_default_exit(self, destination_uuid):
        self.router.update_default_category(destination_uuid)

    def validate(self):
        if self.has_basic_exit:
            raise ValueError('Basic exits are not supported in SwitchRouterNode')
        self.router.validate()

    def _get_exits(self):
        return self.router.get_exits()


class RandomRouterNode(BaseNode):

    def __init__(self, operand, result_name=None, wait_for_message=False, uuid=None):
        super().__init__(uuid)
        self.router = RandomRouter(operand, result_name, wait_for_message)
        self.has_basic_exit = False

    def add_choice(self, **kwargs):
        self.router.add_choice(**kwargs)

    def validate(self):
        if self.has_basic_exit or self.default_exit_uuid:
            raise ValueError('Default exits are not supported in SwitchRouterNode')

        self.router.validate()

    def _get_exits(self):
        return self.router.get_exits()


class EnterFlowNode(BaseNode):
    def __init__(self, flow_name, complete_destination_uuid=None, expired_destination_uuid=None, uuid=None):
        super().__init__(uuid)

        self.add_action(EnterFlowAction(flow_name))

        self.router = SwitchRouter(operand='@child.run.status', result_name=None, wait_for_message=False)
        self.router.default_category.update_name('Expired')

        self.add_choice(comparison_variable='@child.run.status', comparison_type='has_only_text',
                        comparison_arguments=['completed'], category_name='Complete',
                        destination_uuid=complete_destination_uuid)
        self.add_choice(comparison_variable='@child.run.status', comparison_type='has_only_text',
                        comparison_arguments=['expired'], category_name='Expired',
                        destination_uuid=expired_destination_uuid, is_default=True)
        # TODO: Ensure no warnings about overwriting default category

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

