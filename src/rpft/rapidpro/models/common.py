import re

from rpft.rapidpro.models.exceptions import RapidProActionError
from rpft.rapidpro.utils import generate_new_uuid


def mangle_string(string):
    string = re.sub(r"[. ]", "_", string)
    string = re.sub(r"[^A-Za-z0-9\_\-]+", "", string)
    return string[:15]


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
        if self.destination_uuid == "HARD_EXIT":
            return True
        return False

    def render(self):
        destination_uuid = self.destination_uuid
        if self.destination_uuid == "HARD_EXIT":
            destination_uuid = None
        return {
            "destination_uuid": destination_uuid,
            "uuid": self.uuid,
        }


class FlowReference:
    def from_dict(data):
        return FlowReference(**data)

    def __init__(self, name, uuid=None):
        self.name = name
        self.uuid = uuid

    def record_uuid(self, uuid_dict):
        uuid_dict.record_flow_uuid(self.name, self.uuid)

    def assign_uuid(self, uuid_dict):
        self.uuid = uuid_dict.get_flow_uuid(self.name)

    def render(self):
        return {"name": self.name, "uuid": self.uuid}


def generate_field_key(field_name):
    field_key = field_name.strip().lower().replace(" ", "_")
    if not len(field_key) <= 36:
        raise RapidProActionError(
            "Contact field keys should be no longer than 36 characters."
        )
    if not re.search("[A-Za-z]", field_key):
        raise RapidProActionError(
            "Contact field keys should contain at least one letter."
        )
    return field_key


class ContactFieldReference:
    def from_dict(data):
        return ContactFieldReference(**data)

    def __init__(self, name, key=None, type=None):
        self.name = name
        self.key = key or generate_field_key(name)
        self.type = type

    def render(self):
        render_dict = {"name": self.name, "key": self.key}
        if self.type:
            render_dict["type"] = type
        return render_dict

    def render_with_label(self):
        return {"label": self.name, "key": self.key}


class Group:
    def from_dict(data):
        return Group(**data)

    def __init__(
        self, name, uuid=None, query=None, status=None, system=None, count=None
    ):
        self.name = name
        self.uuid = uuid
        self.query = query
        self.status = status
        self.system = system
        self.count = count

    def record_uuid(self, uuid_dict):
        uuid_dict.record_group_uuid(self.name, self.uuid)

    def assign_uuid(self, uuid_dict):
        self.uuid = uuid_dict.get_group_uuid(self.name)

    def render(self):
        render_dict = {"name": self.name, "uuid": self.uuid}
        for attribute in ["query", "status", "system", "count"]:
            value = getattr(self, attribute)
            if value is not None:
                render_dict[attribute] = value
        return render_dict
