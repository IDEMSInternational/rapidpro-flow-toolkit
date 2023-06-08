from rapidpro_flow_tools.rapidpro.utils import generate_new_uuid


class Exit:
    def __init__(self, destination_uuid=None, uuid=None):
        self.uuid = uuid if uuid else generate_new_uuid()
        self.destination_uuid = destination_uuid

    def from_dict(data):
        return Exit(**data)

    def is_hard_exit(self):
        # This is a notion introduced in the context of blocks,
        # which are groups of nodes included in a flow.
        # By default, when attaching nodes to the end of a block, all
        # unconnected exits from the block are connected, however,
        # hard exits are omitted and exit the flow.
        if self.destination_uuid == 'HARD_EXIT':
            return True
        return False

    def render(self):
        destination_uuid = self.destination_uuid
        if self.destination_uuid == 'HARD_EXIT':
            destination_uuid = None
        return {
            'destination_uuid': destination_uuid,
            'uuid': self.uuid,
        }
