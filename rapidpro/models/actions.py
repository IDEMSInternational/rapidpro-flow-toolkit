from rapidpro.utils import generate_new_uuid
import copy

# TODO: Check enter flow
# Node classification:
# - Action-only node (for various actions)
# - No action, split by variable [this includes wait_for_response]
# - Action + split by variable:
# - Enter flow (Router with Completed/Expired)
# - Call webhook (Router with Success/Failure)
# - No action, split by random

class Action:
    def from_dict(data):
        # Create a generic Action, and cast it to the specific Action subclass
        # in order to bypass the constructor of the subclass
        assert "type" in data
        action_type = data['type']
        action = Action(action_type)
        cls = action_map[action_type]
        action.__class__ = cls
        # Fill in the fields of the object
        action._assign_fields_from_dict(data)
        return action

    def _assign_fields_from_dict(self, data):
        self.__dict__ = data

    def __init__(self, type):
        self.uuid = generate_new_uuid()
        self.type = type

    def record_global_uuids(self, uuid_dict):
        pass

    def assign_global_uuids(self, uuid_dict):
        pass

    def render(self):
        return {
            'uuid': self.uuid,
            'type': self.type,
        }


class UnclassifiedAction(Action):
    def render(self):
        return self.__dict__


class SendMessageAction(Action):
    def __init__(self, text, attachments=None, quick_replies=None, all_urns=None):
        super().__init__('send_msg')
        self.text = text
        self.attachments = attachments or list()
        self.quick_replies = quick_replies or list()
        self.all_urns = all_urns

    def add_attachment(self, attachment):
        self.attachments.append(attachment)

    def add_quick_reply(self, quick_reply):
        self.quick_replies.append(quick_reply)

    def render(self):
        # Can we find a more compact way of invoking the superclass
        # to render the common fields?
        render_dict = super().render()
        render_dict.update({
            "text": self.text,
            "attachments": [attachment for attachment in self.attachments if attachment],
            "quick_replies": self.quick_replies,
        })

        # Refactor this into a method to avoid code replication
        if hasattr(self, "all_urns") and self.all_urns:
            render_dict.update({
                'all_urns': self.all_urns
            })
        if hasattr(self, "topic") and self.topic:
            render_dict.update({
                'topic': self.topic
            })
        if hasattr(self, "templating") and self.templating:
            render_dict.update({
                'templating': self.templating
            })

        return render_dict


class SetContactFieldAction(Action):
    def __init__(self, field_name, value):
        super().__init__('set_contact_field')
        self.field_key = self._get_field_key(field_name)
        self.field_name = field_name
        self.value = value

    def _assign_fields_from_dict(self, data):
        assert "field" in data
        data_copy = copy.deepcopy(data)
        field = data_copy.pop("field")
        super()._assign_fields_from_dict(data_copy)
        self.field_key = field["key"]
        self.field_name = field["name"]

    def _get_field_key(self, field_name):
        return field_name.strip().replace(' ', '_')

    def render(self):
        return {
            "uuid": self.uuid,
            "type": self.type,
            "field": {
                "key": self.field_key,
                "name": self.field_name
            },
            "value": self.value
        }


class Group:
    def from_dict(data):
        return Group(**data)

    def __init__(self, name, uuid=None):
        self.name = name
        self.uuid = uuid

    def record_uuid(self, uuid_dict):
        uuid_dict.record_group_uuid(self.name, self.uuid)

    def assign_uuid(self, uuid_dict):
        self.uuid = uuid_dict.get_group_uuid(self.name)

    def render(self):
        return {
            'name': self.name,
            'uuid': self.uuid
        }


class GenericGroupAction(Action):
    def __init__(self, type, groups):
        super().__init__(type)
        self.groups = groups

    def _assign_fields_from_dict(self, data):
        assert "groups" in data
        groups = []
        for group in data["groups"]:
            groups.append(Group.from_dict(group))
        data = copy.deepcopy(data)  # don't mutate the input
        data["groups"] = groups
        super()._assign_fields_from_dict(data)


    def record_global_uuids(self, uuid_dict):
        for group in self.groups:
            group.record_uuid(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        for group in self.groups:
            group.assign_uuid(uuid_dict)

    def render(self):
        return NotImplementedError


class AddContactGroupAction(GenericGroupAction):
    def __init__(self, groups):
        super().__init__('add_contact_groups', groups)

    def add_group(self, group):
        self.groups.append(group)

    def render(self):
        return {
            "type": self.type,
            "uuid": self.uuid,
            "groups": [group.render() for group in self.groups],
        }


class RemoveContactGroupAction(GenericGroupAction):
    def __init__(self, groups, all_groups=None):
        super().__init__('remove_contact_groups', groups)
        self.all_groups = all_groups

    def render(self):
        render_dict = {
            "type": self.type,
            "uuid": self.uuid,
            "groups": [group.render() for group in self.groups],
        }
        if hasattr(self, "all_groups") and self.all_groups:
            render_dict.update({
                'all_groups': self.all_groups
            })
        return render_dict


class SetRunResultAction(Action):
    def __init__(self, name, value, category=''):
        super().__init__('set_run_result')
        self.name = name
        self.value = value
        self.category = category

    def render(self):
        render_dict = {
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "uuid": self.uuid
        }
        if self.category:
            render_dict.update({
                "category": self.category,
            })
        return render_dict


class EnterFlowAction(Action):
    def __init__(self, flow_name, uuid=None):
        super().__init__('enter_flow')
        self.flow = {
            'name': flow_name,
            'uuid': uuid
        }

    def record_global_uuids(self, uuid_dict):
        uuid_dict.record_flow_uuid(self.flow["name"], self.flow["uuid"])

    def assign_global_uuids(self, uuid_dict):
        self.flow["uuid"] = uuid_dict.get_flow_uuid(self.flow["name"])

    def render(self):
        return {
            "type": self.type,
            "uuid": self.uuid,
            "flow": self.flow
        }

action_map = {
    "add_contact_groups" : AddContactGroupAction,
    "add_contact_urn" : UnclassifiedAction,
    "add_input_labels" : UnclassifiedAction,
    "call_classifier" : UnclassifiedAction,
    "call_resthook" : UnclassifiedAction,
    "call_webhook" : UnclassifiedAction,
    "enter_flow" : EnterFlowAction,
    "open_ticket" : UnclassifiedAction,
    "play_audio" : UnclassifiedAction,
    "remove_contact_groups" : RemoveContactGroupAction,
    "say_msg" : UnclassifiedAction,
    "send_broadcast" : UnclassifiedAction,
    "send_email" : UnclassifiedAction,
    "send_msg" : SendMessageAction,
    "set_contact_channel" : UnclassifiedAction,
    "set_contact_field" : SetContactFieldAction,
    "set_contact_language" : UnclassifiedAction,
    "set_contact_name" : UnclassifiedAction,
    "set_contact_status" : UnclassifiedAction,
    "set_contact_timezone" : UnclassifiedAction,
    "set_run_result" : SetRunResultAction,
    "start_session" : UnclassifiedAction,
    "transfer_airtime" : UnclassifiedAction,
}