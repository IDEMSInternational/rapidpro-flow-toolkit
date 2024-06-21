import copy

from rpft.rapidpro.models.common import (
    ContactFieldReference,
    FlowReference,
    Group,
    mangle_string,
)
from rpft.rapidpro.models.exceptions import RapidProActionError
from rpft.rapidpro.utils import generate_new_uuid
from rpft.parsers.creation.flowrowmodel import dict_to_list_of_pairs

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
        if "type" not in data:
            raise RapidProActionError("RapidProAction must have a type.")
        action_type = data["type"]
        # TODO: Can we make this more smooth by invoking subclass constructors?
        # And make the Action class abstract?
        action = Action(action_type)
        cls = action_map[action_type]
        action.__class__ = cls
        # Fill in the fields of the object
        action._assign_fields_from_dict(data)
        return action

    def _assign_fields_from_dict(self, data):
        self.__dict__ = copy.deepcopy(data)

    def __init__(self, type, **kwargs):
        self.uuid = generate_new_uuid()
        self.type = type
        for k, v in kwargs.items():
            setattr(self, k, v)

    def record_global_uuids(self, uuid_dict):
        pass

    def assign_global_uuids(self, uuid_dict):
        pass

    def render(self):
        return {
            "uuid": self.uuid,
            "type": self.type,
        }

    def short_name(self):
        short_type = short_types.get(self.type, self.type)
        short_value = mangle_string(self.main_value())
        return f"{short_type}.{short_value}"

    def main_value(self):
        raise NotImplementedError

    def get_row_model_fields(self):
        # This should probably be an abstract method returning a partially
        # instantiated row model.
        raise NotImplementedError


class DefaultRenderedAction(Action):
    def render(self):
        return self.__dict__

    def get_row_model_fields(self):
        return NotImplementedError


class AddContactURNAction(DefaultRenderedAction):
    def __init__(self, **kwargs):
        super().__init__("add_contact_urn", **kwargs)

    def main_value(self):
        return self.path

    def get_row_model_fields(self):
        return {
            "type": self.type,
            "mainarg_value": self.path,
            "urn_scheme": self.scheme if self.scheme != "tel" else "",
        }


class CallWebhookAction(DefaultRenderedAction):
    def __init__(self, **kwargs):
        super().__init__("call_webhook", **kwargs)

    def main_value(self):
        return self.body

    def get_row_model_fields(self):
        headers = dict_to_list_of_pairs(self.headers)
        return {
            "type": self.type,
            "webhook": {
                "body": self.body,
                "url": self.url,
                "headers": headers,
                "method": self.method,
            },
            "save_name": self.result_name,
        }


class TransferAirtimeAction(DefaultRenderedAction):
    def __init__(self, **kwargs):
        assert "amounts" in kwargs
        super().__init__("transfer_airtime", **kwargs)

    def main_value(self):
        return self.amounts

    def get_row_model_fields(self):
        amounts = {k : str(v) for k, v in self.amounts.items()}
        amounts = dict_to_list_of_pairs(amounts)
        return {
            "type": self.type,
            "mainarg_dict": amounts,
            "save_name": self.result_name,
        }


class WhatsAppMessageTemplating:
    def __init__(self, name, template_uuid, variables, uuid=None):
        self.name = name
        self.uuid = uuid or generate_new_uuid()
        self.template_uuid = template_uuid
        self.variables = variables

    def from_whats_app_templating_model(model):
        return WhatsAppMessageTemplating(
            name=model.name,
            template_uuid=model.uuid,
            variables=model.variables,
        )

    def from_rapid_pro_templating(templating):
        return WhatsAppMessageTemplating(
            templating["template"]["name"],
            templating["template"]["uuid"],
            templating["variables"],
            templating["uuid"],
        )

    def to_whats_app_templating_dict(self):
        return {
            "name": self.name,
            "uuid": self.template_uuid,
            "variables": self.variables,
        }

    def render(self):
        return {
            "template": {
                "name": self.name,
                "uuid": self.template_uuid,
            },
            "uuid": self.uuid,
            "variables": self.variables,
        }


class SendMessageAction(Action):
    def __init__(
        self, text, attachments=None, quick_replies=None, all_urns=None, templating=None
    ):
        super().__init__("send_msg")
        if not text:
            raise RapidProActionError("send_msg action requires non-empty text.")
        self.text = text
        self.attachments = attachments or list()
        self.quick_replies = quick_replies or list()
        self.all_urns = all_urns
        self.templating = templating

    def _assign_fields_from_dict(self, data):
        data_copy = copy.deepcopy(data)
        if "templating" in data:
            templating = data_copy.pop("templating")
        super()._assign_fields_from_dict(data_copy)
        if "templating" in data:
            self.templating = WhatsAppMessageTemplating.from_rapid_pro_templating(
                templating
            )

    def add_attachment(self, attachment):
        self.attachments.append(attachment)

    def add_quick_reply(self, quick_reply):
        self.quick_replies.append(quick_reply)

    def main_value(self):
        return self.text

    def _get_attachments(self):
        return [attachment for attachment in self.attachments if attachment]

    def render(self):
        # Can we find a more compact way of invoking the superclass
        # to render the common fields?
        render_dict = super().render()
        render_dict.update(
            {
                "text": self.text,
                "attachments": self._get_attachments(),
                "quick_replies": self.quick_replies,
            }
        )

        # Refactor this into a method to avoid code replication
        if hasattr(self, "all_urns") and self.all_urns:
            render_dict.update({"all_urns": self.all_urns})
        if hasattr(self, "topic") and self.topic:
            render_dict.update({"topic": self.topic})
        if hasattr(self, "templating") and self.templating:
            render_dict.update({"templating": self.templating.render()})

        return render_dict

    def get_row_model_fields(self):
        # TODO: templating
        attachment_by_type = {}
        attachments = self._get_attachments()
        # If there are more than 1 attachment, we cannot encode their
        # order if we use the image/audio/video column.
        # Thus we only use these if there is exactly one attachment,
        # and otherwise we use the general attachment list.
        if len(attachments) == 1:
            attachment = attachments[0]
            for attachment_type in ["image", "audio", "video"]:
                if attachment.startswith(f"{attachment_type}:"):
                    attachment_by_type[attachment_type] = attachment[6:]
                    attachments = []
                    break

        out_dict = {
            "type": "send_message",
            "mainarg_message_text": self.text,
            "choices": self.quick_replies,
            "image": attachment_by_type.get("image", ""),
            "audio": attachment_by_type.get("audio", ""),
            "video": attachment_by_type.get("video", ""),
            "attachments": attachments,
        }
        if hasattr(self, "templating") and self.templating:
            out_dict.update({
                "wa_template": WhatsAppMessageTemplating.to_whats_app_templating_dict(
                    self.templating
                )
            })
        return out_dict


class SetContactFieldAction(Action):
    def __init__(self, field_name, value):
        super().__init__("set_contact_field")
        self.field = ContactFieldReference(field_name)
        self.value = value
        if len(value) > 640:
            raise RapidProActionError(
                "Contact fields are limited to 640 characters, but value has length"
                f" {len(value)}"
            )

    def _assign_fields_from_dict(self, data):
        assert "field" in data
        data_copy = copy.deepcopy(data)
        data_copy["field"] = ContactFieldReference(**data_copy["field"])
        super()._assign_fields_from_dict(data_copy)

    def main_value(self):
        return self.field.name

    def render(self):
        return {
            "uuid": self.uuid,
            "type": self.type,
            "field": self.field.render(),
            "value": self.value,
        }

    def get_row_model_fields(self):
        return {
            "type": "save_value",
            "mainarg_value": self.value,
            "save_name": self.field.name,
        }


# This action captures the following action types:
# set_contact_channel
# set_contact_language
# set_contact_name
# set_contact_status
# set_contact_timezone
class SetContactPropertyAction(Action):
    def __init__(self, property, value):
        super().__init__(f"set_contact_{property}")
        self.property = property
        if not value:
            raise RapidProActionError(
                f"{property} must be non-empty for set_contact_{property}."
            )
        self.value = value

    def _assign_fields_from_dict(self, data):
        assert "type" in data
        action_type = data["type"]
        assert action_type.find("set_contact_") != -1
        property = action_type.replace("set_contact_", "")
        assert property in data
        assert property in ["channel", "language", "name", "status", "timezone"]
        data_copy = copy.deepcopy(data)
        super()._assign_fields_from_dict(data_copy)
        self.property = property
        self.value = data_copy.pop(property)

    def main_value(self):
        return self.property

    def render(self):
        return {"uuid": self.uuid, "type": self.type, self.property: self.value}

    def get_row_model_fields(self):
        return {
            "type": self.type,
            "mainarg_value": self.value,
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

    def main_value(self):
        return self.groups[0].name

    def render(self):
        return NotImplementedError

    def get_row_model_fields(self):
        # abstract method
        return {
            "mainarg_groups": [group.name for group in self.groups],
            "obj_id": [group.uuid for group in self.groups][0]
            or "",  # 0th element as obj_id is not yet a list.
        }


class AddContactGroupAction(GenericGroupAction):
    def __init__(self, groups):
        super().__init__("add_contact_groups", groups)

    def add_group(self, group):
        self.groups.append(group)

    def render(self):
        return {
            "type": self.type,
            "uuid": self.uuid,
            "groups": [group.render() for group in self.groups],
        }

    def get_row_model_fields(self):
        fields = super().get_row_model_fields()
        fields["type"] = "add_to_group"
        return fields


class RemoveContactGroupAction(GenericGroupAction):
    def __init__(self, groups, all_groups=None):
        super().__init__("remove_contact_groups", groups)
        self.all_groups = all_groups

    def render(self):
        render_dict = {
            "type": self.type,
            "uuid": self.uuid,
            "groups": [group.render() for group in self.groups],
        }
        if hasattr(self, "all_groups") and self.all_groups:
            render_dict.update({"all_groups": self.all_groups})
        return render_dict

    def get_row_model_fields(self):
        fields = super().get_row_model_fields()
        fields["type"] = "remove_from_group"
        return fields


class SetRunResultAction(Action):
    def __init__(self, name, value, category=""):
        super().__init__("set_run_result")
        self.name = name
        self.value = value
        self.category = category
        if len(value) > 640:
            raise RapidProActionError(
                "Flow results are limited to 640 characters, but value has length"
                f" {len(value)}"
            )

    def main_value(self):
        return self.name

    def _assign_fields_from_dict(self, data):
        assert "name" in data
        assert "value" in data
        super()._assign_fields_from_dict(data)
        if "category" not in data:
            self.category = ""

    def render(self):
        render_dict = {
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "uuid": self.uuid,
        }
        if self.category:
            render_dict.update(
                {
                    "category": self.category,
                }
            )
        return render_dict

    def get_row_model_fields(self):
        output_dict = {
            "type": "save_flow_result",
            "mainarg_value": self.value,
            "save_name": self.name,
        }
        if self.category:
            output_dict.update(
                {
                    "result_category": self.category,
                }
            )
        return output_dict


class EnterFlowAction(Action):
    def __init__(self, flow_name, flow_uuid=None):
        super().__init__("enter_flow")
        self.flow = FlowReference(flow_name, flow_uuid)

    def _assign_fields_from_dict(self, data):
        assert "flow" in data
        data = copy.deepcopy(data)  # don't mutate the input
        data["flow"] = FlowReference.from_dict(data["flow"])
        super()._assign_fields_from_dict(data)

    def record_global_uuids(self, uuid_dict):
        self.flow.record_uuid(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        self.flow.assign_uuid(uuid_dict)

    def main_value(self):
        return self.flow.name

    def render(self):
        return {"type": self.type, "uuid": self.uuid, "flow": self.flow.render()}

    def get_row_model_fields(self):
        return {
            "type": "start_new_flow",
            "mainarg_flow_name": self.flow.name,
            "obj_id": self.flow.uuid or "",
        }


action_map = {
    "add_contact_groups": AddContactGroupAction,
    "add_contact_urn": AddContactURNAction,
    "add_input_labels": DefaultRenderedAction,
    "call_classifier": DefaultRenderedAction,
    "call_resthook": DefaultRenderedAction,
    "call_webhook": CallWebhookAction,
    "enter_flow": EnterFlowAction,
    "open_ticket": DefaultRenderedAction,
    "play_audio": DefaultRenderedAction,
    "remove_contact_groups": RemoveContactGroupAction,
    "say_msg": DefaultRenderedAction,
    "send_broadcast": DefaultRenderedAction,
    "send_email": DefaultRenderedAction,
    "send_msg": SendMessageAction,
    "set_contact_channel": SetContactPropertyAction,
    "set_contact_field": SetContactFieldAction,
    "set_contact_language": SetContactPropertyAction,
    "set_contact_name": SetContactPropertyAction,
    "set_contact_status": SetContactPropertyAction,
    "set_contact_timezone": SetContactPropertyAction,
    "set_run_result": SetRunResultAction,
    "start_session": DefaultRenderedAction,
    "transfer_airtime": TransferAirtimeAction,
}

short_types = {
    "call_webhook": "webhook",
    "enter_flow": "flow",
    "send_msg": "msg",
}
