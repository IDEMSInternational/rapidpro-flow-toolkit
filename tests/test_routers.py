import unittest

from rpft.rapidpro.models.exceptions import RapidProRouterError
from rpft.rapidpro.models.routers import SwitchRouter, RandomRouter


class TestRouters(unittest.TestCase):
    def setUp(self) -> None:
        self.switch_router = SwitchRouter(
            operand="@input.text", result_name=None, wait_timeout=600
        )
        self.switch_router.add_choice(
            "@input.text",
            "has_any_word",
            ["word"],
            "Add",
            "test_destination_1",
            is_default=False,
        )
        self.switch_router.add_choice(
            "@input.text",
            "has_any_word",
            ["word"],
            "Other",
            "test_destination_2",
            is_default=True,
        )
        self.switch_router.update_no_response_category("no_response_destination_uuid")

        self.random_router = RandomRouter()
        self.random_router.add_choice("random_1", "test_destination_1")
        self.random_router.add_choice("random_2", "test_destination_2")
        self.random_router.add_choice("random_3", "test_destination_3")

    def test_switch_router_render(self):
        render_output = self.switch_router.render()

        for key in ["type", "categories", "cases", "operand", "default_category_uuid"]:
            self.assertIn(key, list(render_output.keys()))

        self.assertEqual(render_output["type"], "switch")
        self.assertEqual(render_output["operand"], "@input.text")
        self.assertEqual(render_output["cases"][0]["type"], "has_any_word")
        self.assertEqual(render_output["cases"][0]["arguments"], ["word"])

        self.assertEqual(len(render_output["categories"]), 3)
        self.assertEqual(render_output["categories"][0]["name"], "Add")

        self.assertIn("Add", [c["name"] for c in render_output["categories"]])
        self.assertIn("Other", [c["name"] for c in render_output["categories"]])
        self.assertIn("No Response", [c["name"] for c in render_output["categories"]])
        self.assertIn("wait", render_output)
        self.assertEqual(render_output["wait"]["timeout"]["seconds"], 600)
        no_response_category = [
            c for c in render_output["categories"] if c["name"] == "No Response"
        ][0]
        self.assertEqual(
            render_output["wait"]["timeout"]["category_uuid"],
            no_response_category["uuid"],
        )

        other_category_arr = [
            c for c in render_output["categories"] if c["name"] == "Other"
        ]

        self.assertEqual(
            render_output["default_category_uuid"], other_category_arr[0]["uuid"]
        )

    def test_random_router_render(self):
        render_output = self.random_router.render()

        self.assertEqual(render_output["type"], "random")
        for key in ["type", "categories"]:
            self.assertIn(key, list(render_output.keys()))

        category_names = [c["name"] for c in render_output["categories"]]

        for name in ["random_1", "random_2", "random_3"]:
            self.assertIn(name, category_names)


class TestDuplicateChoices(unittest.TestCase):
    def test_switch_router_default(self):
        switch_router = SwitchRouter(operand="@fields.field")
        switch_router.add_choice(
            "@fields.field",
            "has_any_word",
            ["other"],
            "Other",
            "test_destination_1",
            is_default=True,
        )
        switch_router.add_choice(
            "@fields.field",
            "has_any_word",
            ["word"],
            "Word",
            "test_destination_2",
            is_default=False,
        )
        # Duplicate case with different destination
        switch_router.add_choice(
            "@fields.field",
            "has_any_word",
            ["other"],
            "Other",
            "test_destination_3",
            is_default=True,
        )

        render_output = switch_router.render()
        self.assertEqual(len(render_output["cases"]), 2)
        self.assertEqual(len(render_output["categories"]), 2)
        self.assertEqual(render_output["categories"][0]["name"], "Word")
        self.assertEqual(render_output["categories"][1]["name"], "Other")
        self.assertEqual(
            switch_router.default_category.exit.destination_uuid, "test_destination_3"
        )

    def test_switch_router_blank(self):
        switch_router = SwitchRouter(
            operand="@input.text", result_name=None, wait_timeout=600
        )
        switch_router.add_choice(
            "@input.text",
            "has_any_word",
            ["word"],
            "",
            "test_destination_1",
            is_default=False,
        )
        switch_router.update_default_category("test_destination_2")
        # Duplicate case with different destination
        switch_router.add_choice(
            "@input.text",
            "has_any_word",
            ["word"],
            "",
            "test_destination_3",
            is_default=False,
        )
        switch_router.update_no_response_category("no_response_destination_uuid")

        render_output = switch_router.render()
        self.assertEqual(len(render_output["cases"]), 1)
        self.assertEqual(len(render_output["categories"]), 3)
        self.assertEqual(render_output["categories"][0]["name"], "Word")
        cats = [
            category for category in switch_router.categories if category.name == "Word"
        ]
        # There should be exactly one Word category, internally
        self.assertEqual(len(cats), 1)
        self.assertEqual(cats[0].exit.destination_uuid, "test_destination_3")


class TestNoArgsTests(unittest.TestCase):
    def test_no_args_tests(self):
        switch_router = SwitchRouter(operand="@fields.field")
        switch_router.add_choice(
            "@fields.field",
            "has_text",
            ["junk"],
            "Has Text",
            "test_destination_1",
            is_default=False,
        )

        render_output = switch_router.render()
        self.assertEqual(len(render_output["cases"]), 1)
        self.assertEqual(len(render_output["categories"]), 2)
        self.assertEqual(render_output["cases"][0]["arguments"], [])
        self.assertEqual(render_output["categories"][0]["name"], "Has Text")
        self.assertEqual(render_output["categories"][1]["name"], "Other")
        self.assertEqual(switch_router.default_category.exit.destination_uuid, None)
        self.assertEqual(
            switch_router.categories[0].exit.destination_uuid, "test_destination_1"
        )

    def test_invalid_test(self):
        switch_router = SwitchRouter(operand="@fields.field")
        with self.assertRaises(RapidProRouterError):
            switch_router.add_choice(
                "@fields.field",
                "has_junk",
                ["junk"],
                "Has Just",
                "test_destination_1",
                is_default=False,
            )
