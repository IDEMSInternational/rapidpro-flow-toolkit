import unittest

from rpft.rapidpro.models.actions import SendMessageAction
from rpft.rapidpro.models.nodes import BasicNode


class TestNodes(unittest.TestCase):
    def setUp(self) -> None:
        self.basic_node = BasicNode()
        self.basic_node.add_action(SendMessageAction(text='test_message_1', quick_replies=['qr01', 'qr02', 'qr03']))
        self.basic_node.add_action(SendMessageAction(text='test_image_message', attachments=['image:image url']))
        self.basic_node.add_action(SendMessageAction(text='test_audio_message', attachments=['audio:audio url']))

        self.basic_node.update_default_exit('test_destination_uuid')

    def test_basic_node(self):
        render_output = self.basic_node.render()

        action_names = [a['text'] for a in render_output['actions']]

        action_1_index = action_names.index('test_message_1')
        action_2_index = action_names.index('test_image_message')
        action_3_index = action_names.index('test_audio_message')

        self.assertEqual(render_output['actions'][action_1_index]['text'], 'test_message_1')
        self.assertEqual(render_output['actions'][action_2_index]['text'], 'test_image_message')
        self.assertEqual(render_output['actions'][action_3_index]['text'], 'test_audio_message')




