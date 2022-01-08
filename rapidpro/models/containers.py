from rapidpro.utils import generate_new_uuid


class RapidProContainer:
    def __init__(self, campaigns=None, fields=None, flows=None, groups=None, site=None, triggers=None, version='13'):
        self.campaigns = campaigns or []
        self.fields = fields or []
        self.flows = flows or []
        self.groups = groups or []
        self.site = site or 'https://rapidpro.idems.international'
        self.triggers = triggers or []
        self.version = version

    def add_flow(self, flow):
        self.flows.append(flow)

    def update_global_uuids(self, uuid_dict):
        # Prefill with existings flows and groups
        for group in self.groups:
            uuid_dict.record_group_uuid(group.name, group.uuid)
        for flow in self.flows:
            uuid_dict.record_flow_uuid(flow.name, flow.uuid)

        # Update group/flow UUIDs referenced within the flows
        for flow in self.flows:
            flow.record_global_uuids(uuid_dict)
        uuid_dict.generate_missing_uuids()
        for flow in self.flows:
            flow.assign_global_uuids(uuid_dict)
        # TODO: Update self.groups

    def render(self):
        return {
            "campaigns": [], # self.campaigns,
            "fields": [], # self.fields,
            "flows": [flow.render() for flow in self.flows],
            "groups": [], # self.groups,
            "site": self.site,
            "triggers": [], # self.triggers,
            "version": self.version,
        }


class FlowContainer:
    def __init__(self, flow_name, type='messaging', language='eng', uuid=None):
        self.uuid = uuid or generate_new_uuid()
        self.name = flow_name
        self.language = language
        self.type = type
        self.nodes = []
        # 'spec_version': '13.1.0',
        # '_ui': None,
        # 'revision': 0,
        # 'expire_after_minutes': 60,
        # 'metadata': {'revision': 0},
        # 'localization': {}

    def add_node(self, node):
        self.nodes.append(node)

    def record_global_uuids(self, uuid_dict):
        for node in self.nodes:
            node.record_global_uuids(uuid_dict)

    def assign_global_uuids(self, uuid_dict):
        for node in self.nodes:
            node.assign_global_uuids(uuid_dict)

    def render(self):
        return {
            "uuid": self.uuid,
            "name": self.name,
            "language": self.language,
            "type": self.type,
            "nodes": [node.render() for node in self.nodes]
        }


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
        self.record_uuid(self.group_dict, name, uuid)

    def record_flow_uuid(self, name, uuid):
        self.record_uuid(self.flow_dict, name, uuid)

    def record_uuid(self, uuid_dict, name, uuid):
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