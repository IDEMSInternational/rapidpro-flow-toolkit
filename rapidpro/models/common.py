from rapidpro.utils import generate_new_uuid


class Exit:
    def __init__(self, destination_uuid=None, uuid=None):
        self.uuid = uuid if uuid else generate_new_uuid()
        self.destination_uuid = destination_uuid

    def from_dict(data):
        return Exit(**data)

    def render(self):
        return {
            'destination_uuid': self.destination_uuid,
            'uuid': self.uuid,
        }
