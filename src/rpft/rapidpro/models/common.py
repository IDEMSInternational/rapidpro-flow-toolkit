import re

from rpft.rapidpro.models.exceptions import RapidProActionError
from rpft.rapidpro.utils import generate_new_uuid


FIELD_KEY_MAX_LENGTH = 36
RESERVED_FIELD_KEYS = [
    "created_by",
    "created_on",
    "discord",
    "ext",
    "facebook",
    "fcm",
    "first_name",
    "freshchat",
    "groups",
    "has",
    "id",
    "instagram",
    "is",
    "jiochat",
    "language",
    "line",
    "mailto",
    "modified_by",
    "name",
    "rocketchat",
    "scheme",
    "tel",
    "telegram",
    "twitter",
    "twitterid",
    "uuid",
    "viber",
    "vk",
    "wechat",
    "whatsapp",
]


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
    key = field_name.strip().lower().replace(" ", "_")

    if len(key) > FIELD_KEY_MAX_LENGTH:
        raise RapidProActionError(
            "Contact field key length limit exceeded",
            {"length": len(key), "limit": FIELD_KEY_MAX_LENGTH, "key": key},
        )

    if not re.match(r"^[a-z][a-z0-9_]*$", key):
        raise RapidProActionError(
            "Contact field key needs to start with a letter",
            {"key": key, "name": field_name},
        )

    return key


def generate_field_name(field_name):
    # Field names may not contain underscores
    return field_name.replace("_", " ")


class ContactFieldReference:

    def __init__(self, name, key=None, value_type=None):
        self.key = key or generate_field_key(name)
        self.name = generate_field_name(name)
        self.value_type = value_type

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def render(self):
        data = {"key": self.key}

        if self.value_type:
            data["type"] = self.value_type

        return data


class SystemContactField(ContactFieldReference):

    def render(self):
        data = super().render()
        data["label"] = self.name

        return data


class UserContactField(ContactFieldReference):

    def __init__(self, name, key=None, value_type=None):
        super().__init__(name, key, value_type)

        if self.key in RESERVED_FIELD_KEYS:
            raise RapidProActionError(
                "Reserved name used as user contact field key",
                {"name": name, "key": self.key},
            )

    def render(self):
        data = super().render()
        data["name"] = self.name

        return data


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
