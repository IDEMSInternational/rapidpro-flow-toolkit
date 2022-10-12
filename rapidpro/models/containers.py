from rapidpro.utils import generate_new_uuid
from rapidpro.models.nodes import BaseNode
from rapidpro.models.actions import Group
import copy


class RapidProContainer:
    def __init__(self, campaigns=None, fields=None, flows=None, groups=None, site=None, triggers=None, version='13'):
        self.campaigns = campaigns or []
        self.fields = fields or []
        self.flows = flows or []
        self.groups = groups or []
        self.site = site or 'https://rapidpro.idems.international'
        self.triggers = triggers or []
        self.version = version
        self.uuid_dict = UUIDDict()

    def from_dict(data):
        data_copy = copy.deepcopy(data)
        flows = data_copy.pop("flows")
        flows = [FlowContainer.from_dict(flow) for flow in flows]
        groups = data_copy.pop("groups")
        groups = [Group.from_dict(group) for group in groups]
        container = RapidProContainer(**data_copy)
        container.flows = flows
        container.groups = groups
        return container

    def add_flow(self, flow):
        self.flows.append(flow)

    def record_group_uuid(self, name, uuid):
        self.uuid_dict.record_group_uuid(name, uuid)

    def record_flow_uuid(self, name, uuid):
        self.uuid_dict.record_flow_uuid(name, uuid)

    def update_global_uuids(self):
        # Prefill with existings flows and groups
        for group in self.groups:
            self.uuid_dict.record_group_uuid(group.name, group.uuid)
        for flow in self.flows:
            self.uuid_dict.record_flow_uuid(flow.name, flow.uuid)

        # Update group/flow UUIDs referenced within the flows
        for flow in self.flows:
            flow.record_global_uuids(self.uuid_dict)
        self.uuid_dict.generate_missing_uuids()
        for flow in self.flows:
            flow.assign_global_uuids(self.uuid_dict)

    def merge(self, container):
        '''Merge another RapidPro container into this one.

        Should take the union of the flows, groups, etc, and check consistency
        of other parameters (e.g. site)
        '''
        raise NotImplementedError

    def validate(self):
        self.update_global_uuids()
        self.groups = self.uuid_dict.get_group_list()
        # TODO: Update self.fields

    def render(self):
        self.validate()
        return {
            "campaigns": self.campaigns,
            "fields": self.fields,
            "flows": [flow.render() for flow in self.flows],
            "groups": [group.render() for group in self.groups],
            "site": self.site,
            "triggers": self.triggers,
            "version": self.version,
        }


class FlowContainer:
    def __init__(self, flow_name, type='messaging', language='eng', uuid=None, spec_version='13.1.0', revision=0, expire_after_minutes=10080, metadata=None, localization=None, ui=None):
        # UI is not part of this as it is captured within the nodes.
        # Localization/ui may be handled differently in the future (e.g. stored within nodes or similar)
        # The field is likely to be dropped from here, and only here temporarily to avoid losing its data.
        self.uuid = uuid or generate_new_uuid()
        self.name = flow_name
        self.language = language
        self.type = type
        self.nodes = []
        self.spec_version = spec_version
        self.revision = revision
        self.expire_after_minutes = expire_after_minutes
        self.metadata = metadata or {}
        self.localization = localization or {}
        self.ui = ui or {}

    def from_dict(data):
        data_copy = copy.deepcopy(data)
        name = data_copy.pop("name")
        data_copy["flow_name"] = name
        if "_ui" in data_copy:
            ui = data_copy.pop("_ui")
            data_copy["ui"] = ui
        else:
            data_copy["ui"] = {}
        nodes = data_copy.pop("nodes")
        nodes = [BaseNode.from_dict(node) for node in nodes]
        flow_container = FlowContainer(**data_copy)
        flow_container.nodes = nodes
        return flow_container

    def add_node(self, node):
        self.nodes.append(node)

    def record_global_uuids(self, uuid_dict):
        for node in self.nodes:
            node.record_global_uuids(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        for node in self.nodes:
            node.assign_global_uuids(uuid_dict)

    def render(self):
        render_dict = {
            "uuid": self.uuid,
            "name": self.name,
            "language": self.language,
            "type": self.type,
            "nodes": [node.render() for node in self.nodes],
            "spec_version": self.spec_version,
            "revision": self.revision,
            "expire_after_minutes": self.expire_after_minutes,
            "metadata": self.metadata,
            "localization": self.localization
        }
        if self.ui:
            render_dict["_ui"] = self.ui
        return render_dict


class UUIDDict:
    def __init__(self, flow_dict=None, group_dict=None):
        self.flow_dict = flow_dict or {}
        self.group_dict = group_dict or {}

    def generate_missing_uuids(self):
        for k, v in self.flow_dict.items():
            if not v:
                self.flow_dict[k] = generate_new_uuid()
        for k, v in self.group_dict.items():
            if not v:
                self.group_dict[k] = generate_new_uuid()

    def record_group_uuid(self, name, uuid):
        self._record_uuid(self.group_dict, name, uuid)

    def record_flow_uuid(self, name, uuid):
        self._record_uuid(self.flow_dict, name, uuid)

    def _record_uuid(self, uuid_dict, name, uuid):
        recorded_uuid = uuid_dict.get(name)
        if recorded_uuid:
            if uuid and uuid != recorded_uuid:
                raise ValueError(f"Group/Flow {name} has multiple uuids: {uuid} and {recorded_uuid}")
        else:
            uuid_dict[name] = uuid

    def get_group_uuid(self, name):
        return self.group_dict[name]

    def get_flow_uuid(self, name):
        return self.flow_dict[name]

    def get_group_list(self):
        return [Group(name, uuid) for name, uuid in self.group_dict.items()]
