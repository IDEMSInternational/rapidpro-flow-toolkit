import unittest

from rapidpro.models.routers import SwitchRouter, RandomRouter


class TestRouters(unittest.TestCase):
    def setUp(self) -> None:
        self.switch_router = SwitchRouter(operand='@input.text', result_name=None, wait_timeout=None)
        self.switch_router.add_choice('@input.text', 'has_any_word', None, 'Add', 'test_destination_1',
                                      is_default=False)
        self.switch_router.add_choice('@input.text', 'has_any_word', None, 'Other', 'test_destination_2',
                                      is_default=True)

        self.random_router = RandomRouter()
        self.random_router.add_choice('random_1', 'test_destination_1')
        self.random_router.add_choice('random_2', 'test_destination_2')
        self.random_router.add_choice('random_3', 'test_destination_3')

    def test_switch_router_render(self):

        render_output = self.switch_router.render()

        for key in ['type', 'categories', 'cases', 'operand', 'default_category_uuid']:
            self.assertIn(key, list(render_output.keys()))

        self.assertEqual(render_output['type'], 'switch')
        self.assertEqual(render_output['operand'], '@input.text')
        self.assertEqual(render_output['cases'][0]['type'], 'has_any_word')
        self.assertEqual(render_output['cases'][0]['arguments'], None)

        self.assertEqual(len(render_output['categories']), 2)
        self.assertEqual(render_output['categories'][0]['name'], 'Add')

        self.assertIn('Add', [c['name'] for c in render_output['categories']])
        self.assertIn('Other', [c['name'] for c in render_output['categories']])

        other_category_arr = [c for c in render_output['categories'] if c['name'] == 'Other']

        self.assertEqual(render_output['default_category_uuid'], other_category_arr[0]['uuid'])

    def test_random_router_render(self):

        render_output = self.random_router.render()

        self.assertEqual(render_output['type'], 'random')
        for key in ['type', 'categories']:
            self.assertIn(key, list(render_output.keys()))

        category_names = [c['name'] for c in render_output['categories']]

        for name in ['random_1', 'random_2', 'random_3']:
            self.assertIn(name, category_names)
