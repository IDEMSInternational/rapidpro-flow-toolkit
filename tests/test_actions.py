import unittest

from rpft.rapidpro.models.actions import EnterFlowAction


class TestActions(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_enter_flow_node(self):
        enter_flow_node = EnterFlowAction(flow_name='test_flow', flow_uuid='fake-uuid')
        render_output = enter_flow_node.render()
        self.assertEqual(render_output['type'], 'enter_flow')
        self.assertEqual(render_output['flow']['name'], 'test_flow')
        self.assertEqual(render_output['flow']['uuid'], 'fake-uuid')

