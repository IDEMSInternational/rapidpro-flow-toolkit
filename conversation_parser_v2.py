import csv
import json

from constants import nodes_map
from models import RapidProGotoNode, RapidProNode, ConditionalRapidProNode, RapidProExit, SaveNameCollection
from utils import generate_uuid, find_node_with_row_id_only

debug = True


class ReadSheetFromFile:

    def __init__(self, path):
        self.path = path

    def read_csv(self):
        with open(self.path) as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                if row['type'] == 'go_to':
                    goto_node = RapidProGotoNode(
                        row['row_id'],
                        row['type'],
                        row['from'],
                        row['condition'],
                        row['message_text'],
                        row.get('media'),
                        row['choice_1'],
                        row['choice_2'],
                        row['choice_3'],
                        row.get('save_name'),
                    )
                    nodes_map[row['row_id']] = goto_node
                else:
                    rapidpro_node = RapidProNode(
                        row['row_id'],
                        row['type'],
                        row['from'],
                        row['condition'],
                        row['message_text'],
                        row.get('media'),
                        row['choice_1'],
                        row['choice_2'],
                        row.get('choice_3'),
                        row.get('save_name'),
                    )
                    nodes_map[row['row_id']] = rapidpro_node
                line_count += 1

            print(f'Processed {line_count} lines.')


class RapidProParser:
    def populate_base_nodes(self):
        for key, node in nodes_map.items():
            node.parse()

    def run(self):
        all_nodes = []
        for key, node in nodes_map.items():

            node.parse()
            all_nodes.append(node)

            if node.save_name:
                collection = SaveNameCollection(row_id=node.row_id,
                                                type=node.type,
                                                _from=node._from,
                                                condition=node.condition,
                                                message_text=node.message_text,
                                                media=node.media,
                                                choice_1=node.choice_1,
                                                choice_2=node.choice_2,
                                                choice_3=node.choice_3,
                                                save_name=node.save_name,
                                                base_node=node)
                collection.parse()

                next_node = find_node_with_row_id_only(nodes_map=nodes_map, from_row_id=node.row_id)
                collection.add_collection_exit(destination_uuid=next_node.uuid)

                all_nodes.pop()

                all_nodes.extend(collection.get_nodes())

            else:
                if any([node.choice_1, node.choice_2, node.choice_3]):
                    conditional_node = ConditionalRapidProNode(
                        row_id=node.row_id,
                        type=node.type,
                        _from=node._from,
                        condition=node.condition,
                        message_text=node.message_text,
                        media=node.media,
                        choice_1=node.choice_1,
                        choice_2=node.choice_2,
                        choice_3=node.choice_3,
                        save_name=node.save_name,
                    )
                    conditional_node.parse()
                    all_nodes.append(conditional_node)

                    node.add_exit(RapidProExit(conditional_node.uuid))

        print('=======ALL NODES=======')
        print(json.dumps([node.render() for node in all_nodes if node.type != 'go_to']))

        print('========== RAPID PRO JSON==========')
        print(json.dumps(
            {
                'campaigns': [],
                'fields': [],
                'flows': [{
                    'name': f'some_sheet_name',
                    'uuid': generate_uuid(),
                    'spec_version': '13.1.0',
                    'language': 'base',
                    'type': 'messaging',
                    'nodes': [node.render() for node in all_nodes if node.type != 'go_to'],
                    '_ui': None,
                    'revision': 0,
                    'expire_after_minutes': 60,
                    'metadata': {'revision': 0},
                    'localization': {}
                }],
                'groups': [],
                'site': 'https://rapidpro.idems.international',
                'triggers': [],
                'version': '13',
            }

        ))

        print('=================== DEBUG ===============')
        print([node.__class__ for node in all_nodes if node.type != 'go_to'])


if __name__ == '__main__':
    sheets = ['example_story1', 'example_media']

    for sheet_name in sheets:
        path = '/Users/ehmadzubair/Documents/cogent-labs/software-projects/conversation-parser-project/test-spreadsheet - example_media.csv'
        sheet_reader = ReadSheetFromFile(path)
        sheet_reader.read_csv()

        parser = RapidProParser()
        parser.run()
