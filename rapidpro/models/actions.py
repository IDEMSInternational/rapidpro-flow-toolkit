from rapidpro.utils import generate_new_uuid

# TODO: Check enter flow
# Node classification:
# - Action-only node (for various actions)
# - No action, split by variable [this includes wait_for_response]
# - Action + split by variable:
# - Enter flow (Router with Completed/Expired)
# - Call webhook (Router with Success/Failure)
# - No action, split by random


class Action:
    def __init__(self, type):
        self.uuid = generate_new_uuid()
        self.type = type

    def render(self):
        return {
            'uuid': self.uuid,
            'type': self.type,
        }


class SendMessageAction(Action):
    # TODO: Don't use mutable default values (bad things will happen)
    def __init__(self, text, attachments=[], quick_replies=[], all_urns=None):
        super().__init__('send_msg')
        self.text = text
        self.attachments = attachments
        self.quick_replies = quick_replies
        self.all_urns = all_urns

    def add_quick_reply(self, quick_reply):
        self.quick_replies.append(quick_reply)

    def render(self):
        # Can we find a more compact way of invoking the superclass
        # to render the common fields?
        render_dict = super().render()
        render_dict.update({
            "text": self.text,
            "attachments": self.attachments,
            "quick_replies": self.quick_replies,
        })

        if self.all_urns:
            render_dict.update({
                'all_urns': self.all_urns
            })

        return render_dict


class SetContactFieldAction(Action):
    def __init__(self, field_key, field_name, value):
        super().__init__('set_contact_field')
        self.field_key = field_key
        self.field_name = field_name
        self.value = value

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


class GenericGroupAction(Action):
    def __init__(self, type, group_names):
        super().__init__(type)
        self.groups = [{
            'name': group_name  # We add group UUIDs during the validation step
        } for group_name in group_names]

    def add_group(self, group_name):
        self.groups.append({
            'name': group_name
        })

    def render(self):
        return NotImplementedError


class AddContactGroupAction(GenericGroupAction):
    def __init__(self, group_names):
        super().__init__('add_contact_groups', group_names)

    def add_group(self, group_name):
        self.groups.append({
            'name': group_name
        })

    def render(self):
        return {
            "type": self.type,
            "uuid": self.uuid,
            "groups": self.groups,
        }


class RemoveContactGroupAction(GenericGroupAction):
    def __init__(self, group_names, all_groups=None):
        super().__init__('remove_contact_groups', group_names)
        self.all_groups = all_groups

    def render(self):
        render_dict = {
            "type": self.type,
            "uuid": self.uuid,
            "groups": self.groups,
        }
        if self.all_groups:
            render_dict.update({
                'all_groups': self.all_groups
            })
        return render_dict


class SetRunResultAction(Action):
    def __init__(self, name, value, category):
        super().__init__('set_run_result')
        self.name = name
        self.value = value
        self.category = category

    def render(self):
        return {
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "category": self.category,
            "uuid": self.uuid
        }


class EnterFlowAction(Action):
    def __init__(self, flow_name):
        super().__init__('enter_flow')
        self.flow = {
            'name': flow_name,
            'uuid': generate_new_uuid()
        }

    def render(self):
        return {
            "type": self.type,
            "uuid": self.uuid,
            "flow": self.flow
        }

