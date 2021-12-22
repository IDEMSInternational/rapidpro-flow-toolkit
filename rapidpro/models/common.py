from rapidpro.utils import generate_new_uuid


class Exit:
    def __init__(self, destination_uuid=None, exit_uuid=None):
        self.uuid = exit_uuid if exit_uuid else generate_new_uuid()
        self.destination_uuid = destination_uuid


    def render(self):
        return {
            'destination_uuid': self.destination_uuid,
            'uuid': self.uuid,
        }


