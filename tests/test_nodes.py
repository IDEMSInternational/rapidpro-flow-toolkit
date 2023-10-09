import unittest

from rpft.rapidpro.models.actions import SendMessageAction
from rpft.rapidpro.models.nodes import BasicNode, CallWebhookNode


class TestNodes(unittest.TestCase):
    def test_basic_node(self):
        self.basic_node = BasicNode()
        self.basic_node.add_action(
            SendMessageAction(
                text="test_message_1", quick_replies=["qr01", "qr02", "qr03"]
            )
        )
        self.basic_node.add_action(
            SendMessageAction(
                text="test_image_message", attachments=["image:image url"]
            )
        )
        self.basic_node.add_action(
            SendMessageAction(
                text="test_audio_message", attachments=["audio:audio url"]
            )
        )
        self.basic_node.update_default_exit("test_destination_uuid")

        render_output = self.basic_node.render()

        action_names = [a["text"] for a in render_output["actions"]]

        action_1_index = action_names.index("test_message_1")
        action_2_index = action_names.index("test_image_message")
        action_3_index = action_names.index("test_audio_message")

        self.assertEqual(
            render_output["actions"][action_1_index]["text"], "test_message_1"
        )
        self.assertEqual(
            render_output["actions"][action_2_index]["text"], "test_image_message"
        )
        self.assertEqual(
            render_output["actions"][action_3_index]["text"], "test_audio_message"
        )

    def test_webhook_node(self):
        node = CallWebhookNode(
            body="Webhook Body",
            method="GET",
            url="http://localhost:49998/?cmd=success",
            headers={"Authorization": "Token AAFFZZHH"},
            result_name="webhook_result",
        )
        render_output = node.render()

        action_exp = {
            "type": "call_webhook",
            "body": "Webhook Body",
            "method": "GET",
            "url": "http://localhost:49998/?cmd=success",
            "headers": {"Authorization": "Token AAFFZZHH"},
            "result_name": "webhook_result",
        }

        render_output["actions"][0].pop("uuid")
        self.assertEqual(render_output["actions"][0], action_exp)
        router = render_output["router"]
        self.assertEqual(router["type"], "switch")
        self.assertEqual(router["operand"], "@results.webhook_result.category")
        self.assertEqual(len(router["cases"]), 1)
        self.assertEqual(len(router["categories"]), 2)
