from unittest import TestCase

from rpft.parsers.common.cellparser import TemplatePreserver


class TestTemplatePreserver(TestCase):

    def test_templates_preserved_when_splitting_into_list(self):
        parser = TemplatePreserver()
        data = [
            ("{{test}}|", ["{{test}}"], "Single string template with pipe"),
            ("{{ test }} | ", ["{{ test }}"], "Single string template pipe and spaces"),
            ("{{test}};", ["{{test}}"], "Single string template with semi-colon"),
            (
                "{{ test }} ; ",
                ["{{ test }}"],
                "Single string template with semi-colon and spaces",
            ),
            (
                "{@ test @} |",
                ["{@ test @}"],
                "Single native type template with pipe and spaces",
            ),
            (
                "{@ test @} ;",
                ["{@ test @}"],
                "Single native type template with semi-colon and spaces",
            ),
            (
                "{@ something @} | something | {{ blah }}",
                ["{@ something @}", "something", "{{ blah }}"],
                "Native type, string, string template, with pipes",
            ),
            (
                "{@ something @} ; something ; {{ blah }}",
                ["{@ something @}", "something", "{{ blah }}"],
                "Native type, string, string template, with semi-colons",
            ),
            (
                "{{3*(steps.values()|length -1)}};{{3*(steps.values()|length -1)+2}}",
                [
                    "{{3*(steps.values()|length -1)}}",
                    "{{3*(steps.values()|length -1)+2}}",
                ],
                "Real-life example",
            ),
            ("A | B | C", ["A", "B", "C"], "No templates"),
        ]

        for string, expected, message in data:
            self.assertEqual(
                parser.split_into_lists(string),
                expected,
                message,
            )
