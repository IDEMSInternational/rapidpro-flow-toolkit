import copy

from rpft.rapidpro.utils import generate_new_uuid
from rpft.rapidpro.models.common import Group, FlowReference, ContactFieldReference


class CampaignEvent:
    def __init__(
        self,
        offset,
        unit,
        event_type,
        delivery_hour,
        start_mode,
        uuid=None,
        relative_to=None,
        relative_to_key=None,
        relative_to_label=None,
        message=None,
        flow=None,
        flow_name=None,
        flow_uuid=None,
        base_language=None,
    ):
        self.uuid = uuid if uuid else generate_new_uuid()
        self.offset = offset
        self.unit = unit
        self.event_type = event_type
        self.delivery_hour = delivery_hour
        self.message = message  # dict, keys: language IDs, values: message text
        self.relative_to = relative_to or ContactFieldReference(
            relative_to_label, relative_to_key
        )
        self.start_mode = start_mode
        self.flow = flow or FlowReference(flow_name, flow_uuid)
        self.base_language = base_language
        if event_type == "M" and (message is None or base_language is None):
            raise ValueError(
                "CampaignEvent must have a message and base_language if the event_type"
                " is M"
            )
        if event_type == "F" and self.flow is None:
            raise ValueError("CampaignEvent must have a flow if the event_type is F")

    def from_dict(data):
        data_copy = copy.deepcopy(data)
        # What is called 'label' here is normally it's called 'name' for contact fields.
        data_copy["relative_to"] = ContactFieldReference(
            data_copy["relative_to"]["label"], data_copy["relative_to"]["key"]
        )
        if "flow" in data_copy:
            data_copy["flow"] = FlowReference(**data_copy["flow"])
        return CampaignEvent(**data_copy)

    def record_global_uuids(self, uuid_dict):
        if self.flow is not None:
            self.flow.record_uuid(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        if self.flow is not None:
            self.flow.assign_uuid(uuid_dict)

    def render(self):
        render_dict = {
            "uuid": self.uuid,
            "offset": self.offset,
            "unit": self.unit,
            "event_type": self.event_type,
            "delivery_hour": self.delivery_hour,
            "message": self.message,
            "relative_to": self.relative_to.render_with_label(),
            "start_mode": self.start_mode,
        }
        if self.event_type == "F" and self.flow:
            render_dict.update({"flow": self.flow.render()})
        if self.event_type == "M" and self.base_language:
            render_dict.update({"base_language": self.base_language})
        return render_dict


class Campaign:
    def __init__(
        self, name, group=None, group_name=None, group_uuid=None, events=None, uuid=None
    ):
        self.name = name
        self.group = group or Group(group_name, group_uuid)
        self.uuid = uuid if uuid else generate_new_uuid()
        self.events = events or []

    def add_event(self, event):
        self.events.append(event)

    def from_dict(data):
        assert "group" in data
        assert "name" in data
        assert "events" in data
        return Campaign(
            uuid=data.get("uuid"),
            name=data["name"],
            group=Group.from_dict(data["group"]),
            events=[CampaignEvent.from_dict(event) for event in data["events"]],
        )

    def record_global_uuids(self, uuid_dict):
        for event in self.events:
            event.record_global_uuids(uuid_dict)
        self.group.record_uuid(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        for event in self.events:
            event.assign_global_uuids(uuid_dict)
        self.group.assign_uuid(uuid_dict)

    def render(self):
        return {
            "group": self.group.render(),
            "name": self.name,
            "uuid": self.uuid,
            "events": [event.render() for event in self.events],
        }
