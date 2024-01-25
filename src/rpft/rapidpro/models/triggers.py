import copy
from itertools import zip_longest

from rpft.rapidpro.models.common import FlowReference, Group


class Trigger:

    def __init__(
        self,
        trigger_type,
        keyword=None,
        channel=None,
        flow=None,
        flow_name=None,
        flow_uuid=None,
        groups=None,
        group_names=None,
        group_uuids=None,
    ):
        self.trigger_type = trigger_type
        self.keyword = keyword or None
        self.channel = channel or None
        if not flow and not flow_name:
            raise ValueError("Trigger must have flow or a flow_name")
        self.flow = flow or FlowReference(flow_name, flow_uuid)
        if groups is not None:
            self.groups = groups
        else:
            self.groups = []
            for group_name, group_uuid in zip_longest(group_names, group_uuids):
                if not group_name:
                    raise ValueError("Trigger group must have a name.")
                group = Group(group_name, group_uuid or None)
                self.groups.append(group)

    def from_dict(data):
        data_copy = copy.deepcopy(data)
        if "flow" in data_copy:
            data_copy["flow"] = FlowReference(**data_copy["flow"])
        groups = []
        for group in data_copy["groups"]:
            groups.append(Group.from_dict(group))
        data_copy["groups"] = groups
        return Trigger(**data_copy)

    def record_global_uuids(self, uuid_dict):
        if self.flow is not None:
            self.flow.record_uuid(uuid_dict)
        if self.groups is not None:
            for group in self.groups:
                group.record_uuid(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        if self.flow is not None:
            self.flow.assign_uuid(uuid_dict)
        if self.groups is not None:
            for group in self.groups:
                group.assign_uuid(uuid_dict)

    def render(self):
        return {
            "trigger_type": self.trigger_type,
            "keyword": self.keyword,
            "channel": self.channel,
            "flow": self.flow.render(),
            "groups": [group.render() for group in self.groups],
        }
