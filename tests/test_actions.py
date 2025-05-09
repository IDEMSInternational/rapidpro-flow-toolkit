from unittest import TestCase

from rpft.rapidpro.models.actions import EnterFlowAction
from rpft.rapidpro.models.common import generate_field_key
from rpft.rapidpro.models.exceptions import RapidProActionError


class TestActions(TestCase):

    def test_enter_flow_node(self):
        out = EnterFlowAction(flow_name="test_flow", flow_uuid="fake-uuid").render()

        self.assertEqual(out["type"], "enter_flow")
        self.assertEqual(out["flow"]["name"], "test_flow")
        self.assertEqual(out["flow"]["uuid"], "fake-uuid")


class TestFieldKeyGenerator(TestCase):

    def test_generate_key_from_field_name(self):
        self.assertEqual(
            generate_field_key(" Field Name "),
            "field_name",
        )

    def test_generate_keys_up_to_max_length_limit(self):
        self.assertIsNotNone(generate_field_key("x" * 36))

    def test_fail_if_max_key_length_exceeded(self):
        with self.assertRaises(RapidProActionError):
            generate_field_key("z" * 37)

    def test_fail_if_key_does_not_start_with_letter(self):
        with self.assertRaises(RapidProActionError):
            generate_field_key("1zx")
