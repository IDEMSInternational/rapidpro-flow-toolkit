from rapidpro.utils import generate_new_uuid


class Container:
    def __init__(self, flow_name, type='messaging', language='eng'):
        self.uuid = generate_new_uuid()
        self.name = flow_name
        self.language = language
        self.type = type
        self.nodes = []

    def add_node(self, node):
        self.nodes.append(node)

    def render(self):
        return {
            "uuid": self.uuid,
            "name": self.name,
            "language": self.language,
            "type": self.type,
            "nodes": [node.render() for node in self.nodes]
        }
