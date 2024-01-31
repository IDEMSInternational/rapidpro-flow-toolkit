import copy
from itertools import zip_longest

from rpft.rapidpro.models.common import FlowReference, Group


class RapidProTriggerError(Exception):
    pass


class Trigger:
    def __init__(
        self,
        trigger_type,
        keywords=None,
        channel=None,
        match_type=None,
        flow=None,
        flow_name=None,
        flow_uuid=None,
        groups=None,
        group_names=None,
        group_uuids=None,
        exclude_groups=None,
        exclude_group_names=None,
        exclude_group_uuids=None,
    ):
        self.trigger_type = trigger_type
        self.keywords = keywords or []
        self.match_type = match_type or None
        if self.trigger_type == "K":
            if not keywords or not keywords[0]:
                raise ValueError('Triggers of type "K" must have a keyword')
            if not match_type:
                self.match_type = "F"
        self.channel = channel or None
        if not flow and not flow_name:
            raise ValueError("Trigger must have flow or a flow_name")
        self.flow = flow or FlowReference(flow_name, flow_uuid)
        if groups is not None:
            self.groups = groups
        else:
            self.groups = []
            self._assign_groups(self.groups, group_names, group_uuids)
        if exclude_groups is not None:
            self.exclude_groups = exclude_groups
        else:
            self.exclude_groups = []
            if exclude_group_names is not None:
                self._assign_groups(
                    self.exclude_groups,
                    exclude_group_names,
                    exclude_group_uuids
                )

    def _assign_groups(self, groups_field, group_names, group_uuids):
        for group_name, group_uuid in zip_longest(group_names, group_uuids):
            if not group_name:
                raise ValueError("Trigger group must have a name.")
            group = Group(group_name, group_uuid or None)
            groups_field.append(group)

    def from_dict(data):
        data_copy = copy.deepcopy(data)
        if "flow" in data_copy:
            data_copy["flow"] = FlowReference(**data_copy["flow"])
        groups = []
        for group in data_copy["groups"]:
            groups.append(Group.from_dict(group))
        data_copy["groups"] = groups
        if "exclude_groups" in data_copy:
            exclude_groups = []
            for group in data_copy["exclude_groups"]:
                exclude_groups.append(Group.from_dict(group))
            data_copy["exclude_groups"] = exclude_groups
        # Newer versions of RapidPro use a list of keywords instead of a single keyword
        # If we have "keywords", use that. Otherwise, process the "keyword" entry
        if "keywords" not in data_copy:
            assert "keyword" in data_copy
            data_copy["keywords"] = []
            if data_copy["keyword"] is not None:
                data_copy["keywords"].append(data_copy["keyword"])
        if "keyword" in data_copy:
            data_copy.pop("keyword")
        return Trigger(**data_copy)

    def record_global_uuids(self, uuid_dict, require_existing=False):
        if require_existing:
            if not uuid_dict.contains_flow(self.flow.name):
                raise RapidProTriggerError(
                    f"Trigger references undefined flow name {self.flow.name}"
                )
        if self.flow is not None:
            self.flow.record_uuid(uuid_dict)
        if self.groups is not None:
            for group in self.groups:
                group.record_uuid(uuid_dict)
        if self.exclude_groups is not None:
            for group in self.exclude_groups:
                group.record_uuid(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        if self.flow is not None:
            self.flow.assign_uuid(uuid_dict)
        if self.groups is not None:
            for group in self.groups:
                group.assign_uuid(uuid_dict)
        if self.exclude_groups is not None:
            for group in self.exclude_groups:
                group.assign_uuid(uuid_dict)

    def render(self):
        # We include both keywords and keyword in the render output
        # in order to support both newer and older versions of RapidPro
        render_dict = {
            "trigger_type": self.trigger_type,
            "keyword": self.keywords[0] if self.keywords else None,
            "keywords": self.keywords,
            "channel": self.channel,
            "flow": self.flow.render(),
            "groups": [group.render() for group in self.groups],
            "exclude_groups": [group.render() for group in self.exclude_groups],
        }
        if self.match_type:
            render_dict.update({"match_type": self.match_type})
        return render_dict
