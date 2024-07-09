import copy

from rpft.parsers.common.cellparser import CellParser
from rpft.parsers.common.rowdatasheet import RowDataSheet
from rpft.parsers.common.rowparser import RowParser
from rpft.parsers.creation.flowrowmodel import Edge, FlowRowModel
from rpft.rapidpro.models.actions import Group
from rpft.rapidpro.models.campaigns import Campaign
from rpft.rapidpro.models.nodes import BaseNode
from rpft.rapidpro.models.triggers import Trigger
from rpft.rapidpro.utils import generate_new_uuid


class RapidProContainer:
    def __init__(
        self,
        campaigns=None,
        fields=None,
        flows=None,
        groups=None,
        site=None,
        triggers=None,
        version="13",
    ):
        self.campaigns = campaigns or []
        self.fields = fields or []
        self.flows = flows or []
        self.groups = groups or []
        self.site = site or "https://rapidpro.idems.international"
        self.triggers = triggers or []
        self.version = version
        self.uuid_dict = UUIDDict()

    def from_dict(data):
        data_copy = copy.deepcopy(data)
        flows = data_copy.pop("flows")
        flows = [FlowContainer.from_dict(flow) for flow in flows]
        groups = data_copy.pop("groups")
        groups = [Group.from_dict(group) for group in groups]
        campaigns = data_copy.pop("campaigns")
        campaigns = [Campaign.from_dict(campaign) for campaign in campaigns]
        container = RapidProContainer(**data_copy)
        triggers = data_copy.pop("triggers")
        triggers = [Trigger.from_dict(trigger) for trigger in triggers]
        container.flows = flows
        container.groups = groups
        container.campaigns = campaigns
        container.triggers = triggers
        return container

    def add_flow(self, flow):
        self.flows.append(flow)
        self.record_flow_uuid(flow.name, flow.uuid)

    def add_campaign(self, campaign):
        self.campaigns.append(campaign)

    def add_trigger(self, trigger):
        self.triggers.append(trigger)

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
        for campaign in self.campaigns:
            campaign.record_global_uuids(self.uuid_dict)
        for trigger in self.triggers:
            trigger.record_global_uuids(self.uuid_dict, require_existing=True)
        self.uuid_dict.generate_missing_uuids()
        for flow in self.flows:
            flow.assign_global_uuids(self.uuid_dict)
        for campaign in self.campaigns:
            campaign.assign_global_uuids(self.uuid_dict)
        for trigger in self.triggers:
            trigger.assign_global_uuids(self.uuid_dict)

    def merge(self, container):
        """Merge another RapidPro container into this one.

        Should take the union of the flows, groups, etc, and check consistency
        of other parameters (e.g. site)
        """
        raise NotImplementedError

    def validate(self):
        self.update_global_uuids()
        self.groups = self.uuid_dict.get_group_list()
        # TODO: Update self.fields

    def render(self):
        self.validate()
        return {
            "campaigns": [campaign.render() for campaign in self.campaigns],
            "fields": self.fields,
            "flows": [flow.render() for flow in self.flows],
            "groups": [group.render() for group in self.groups],
            "site": self.site,
            "triggers": [trigger.render() for trigger in self.triggers],
            "version": self.version,
        }


class FlowContainer:
    def __init__(
        self,
        flow_name,
        type="messaging",
        language="eng",
        uuid=None,
        spec_version="13.1.0",
        revision=0,
        expire_after_minutes=10080,
        metadata=None,
        localization=None,
    ):
        # UI is not part of this as it is captured within the nodes.
        # Localization may be handled differently in the future (e.g. stored within
        # nodes or similar);
        # it is likely to be dropped from here, and only here temporarily to avoid
        # losing its data.
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

    def from_dict(data):
        data_copy = copy.deepcopy(data)
        name = data_copy.pop("name")
        data_copy["flow_name"] = name
        nodes = data_copy.pop("nodes")
        nodes = [BaseNode.from_dict(node) for node in nodes]
        if "_ui" in data_copy:
            ui = data_copy.pop("_ui")
            if "nodes" in ui:
                for node in nodes:
                    node.add_ui_from_dict(ui["nodes"])
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
            "localization": self.localization,
        }
        ui_dict = {}
        for node in self.nodes:
            node_ui = node.render_ui()
            if node_ui:
                ui_dict[node.uuid] = node_ui
        if ui_dict:
            render_dict["_ui"] = {"nodes": ui_dict}
        return render_dict

    def find_node(self, uuid):
        for node in self.nodes:
            if node.uuid == uuid:
                return node
        raise ValueError(f"Destination node {uuid} does not exist within flow.")

    def _to_rows_recurse(self, node, parent_edge):
        # The version of the graph encoded in a sheet is always a DAG, if we disregard
        # all go_to edges.
        # So we effectively do the DFS version of topological sort here, with the one
        # special case that if we encounter a backward edge (and thus a cycle), we
        # convert it into a go_to edge.
        # We use temporary row_ids here (derived from node uuids) that get converted to
        # sequential ids later.
        self.visited_nodes.add(node.uuid)
        temp_row_id = f"{node.uuid}|{node.short_name()}"
        # Initiate the row model(s) for the node with one incoming edge.
        # More edges may be added later throughout the DFS
        node.initiate_row_models(temp_row_id, parent_edge)
        # Outgoing edges from the nodes (as pairs of exits with edge objects).
        # Each edge will be added as an incoming edge to the node
        # pointed to by the corresponding exit
        exits_edges = node.get_exit_edge_pairs()
        # We go backwards through the outgoing edges:
        # This way, the nodes in the right-most branch will be completed first,
        # and thus appear last in the sheet.
        for exit, edge in exits_edges[::-1]:
            if not exit.destination_uuid:
                # If the edge leads nowhere, there's no way of encoding it in the sheet
                # format.
                # In practice, this means that cases/categories from routers may be
                # dropped if they are not connected to anything.
                continue
            child_node = self.find_node(exit.destination_uuid)
            if child_node.uuid in self.completed_nodes:
                # Edge to a later node.
                # We prepend, so that in the end,
                # the edges are in the correct order again, as in this for
                # loop we go through the edges in reverse order.
                child_node.prepend_edge_to_row_models(edge)
            elif child_node.uuid in self.visited_nodes:
                # This is a backward edge to an ancestor of this node.
                child_row_id = child_node.get_row_models()[0].row_id
                child_short_id = child_row_id.split("|")[1]
                self.rows.insert(
                    0,
                    FlowRowModel(
                        row_id=f"{generate_new_uuid()}|goto.{child_short_id}",
                        type="go_to",
                        edges=[edge],
                        mainarg_destination_row_ids=[child_row_id],
                    ),
                )
            else:
                # A new node we haven't encountered yet
                self._to_rows_recurse(child_node, edge)
        self.completed_nodes.add(node.uuid)
        # Completed row get prepended to our list, in accordance
        # with the topological sort algorithm.
        # Note: These row_models may still be modified in the
        # next steps via other incoming edges.
        self.rows = node.get_row_models() + self.rows

    def to_rows(self, numbered=False):
        if not self.nodes:
            return []
        # TODO: We might want to have a dedicated model for a list of rows
        # that can also contain metadata, used for generating a sheet.
        # TODO: These attributes pollute the namespace of the class,
        # remove them or put them into a separate class.
        self.visited_nodes = set()
        self.completed_nodes = set()
        self.rows = []
        for node in self.nodes:
            node.clear_row_model()
        # Generate the list of rows (with temp row_ids)
        self._to_rows_recurse(self.nodes[0], Edge(from_="start"))
        # We now have to remap the temp row_ids to a sequence of numbers
        # Compile the remapping dict
        temp_row_id_to_row_id = {"start": "start"}
        for idx, row in enumerate(self.rows):
            if numbered:
                new_id = str(idx + 1)
            else:
                # split off the preceding UUID
                new_base_id = row.row_id.split("|")[1]
                # Append a number (if necessary) to ensure uniqueness
                new_id = new_base_id
                counter = 1
                while new_id in temp_row_id_to_row_id.values():
                    new_id = f"{new_base_id}.{counter}"
                    counter += 1
            temp_row_id_to_row_id[row.row_id] = new_id
        # Do the remapping
        for row in self.rows:
            row.row_id = temp_row_id_to_row_id[row.row_id]
            # Also remap ids when referenced in a go_to or in an edge.
            if row.type == "go_to":
                row.mainarg_destination_row_ids = [
                    temp_row_id_to_row_id[row_id]
                    for row_id in row.mainarg_destination_row_ids
                ]
            for edge in row.edges:
                edge.from_ = temp_row_id_to_row_id[edge.from_]
        return self.rows

    def to_row_data_sheet(self, strip_uuids=False, numbered=False):
        target_headers = {"edges.*.condition"}
        excluded_headers = {"obj_id", "_nodeId"} if strip_uuids else {}
        rows = self.to_rows(numbered)
        row_parser = RowParser(FlowRowModel, CellParser())
        return RowDataSheet(row_parser, rows, target_headers, excluded_headers)


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
                raise ValueError(
                    f"Group/Flow {name} has multiple uuids: {uuid} and {recorded_uuid}"
                )
        else:
            uuid_dict[name] = uuid

    def get_group_uuid(self, name):
        return self.group_dict[name]

    def get_flow_uuid(self, name):
        return self.flow_dict[name]

    def contains_flow(self, name):
        return name in self.flow_dict

    def get_group_list(self):
        return [Group(name, uuid) for name, uuid in self.group_dict.items()]
