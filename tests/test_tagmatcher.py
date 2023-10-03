import unittest
from rpft.parsers.creation.tagmatcher import TagMatcher


class TestTagMatcher(unittest.TestCase):
    def test_empty_matcher(self):
        tm = TagMatcher()
        self.assertTrue(tm.matches([]))
        self.assertTrue(tm.matches([""]))
        self.assertTrue(tm.matches(["", ""]))
        self.assertTrue(tm.matches(["tag1", "tag2"]))

    def test_single_tag(self):
        tm = TagMatcher(["1", "foo", "bar"])
        self.assertTrue(tm.matches([]))
        self.assertTrue(tm.matches([""]))
        self.assertTrue(tm.matches(["", ""]))
        self.assertTrue(tm.matches(["", "something"]))
        self.assertTrue(tm.matches(["foo"]))
        self.assertTrue(tm.matches(["bar"]))
        self.assertTrue(tm.matches(["bar", "something"]))
        self.assertFalse(tm.matches(["something"]))
        self.assertFalse(tm.matches(["something", "foo"]))
        self.assertFalse(tm.matches(["something", "bar"]))

    def test_two_tags(self):
        tm = TagMatcher(["1", "foo", "bar", "2", "baz"])
        self.assertTrue(tm.matches([]))
        self.assertTrue(tm.matches([""]))
        self.assertTrue(tm.matches(["", ""]))
        self.assertTrue(tm.matches(["", "baz"]))
        self.assertTrue(tm.matches(["foo", ""]))
        self.assertTrue(tm.matches(["foo", "baz"]))
        self.assertTrue(tm.matches(["bar", "baz"]))
        self.assertTrue(tm.matches(["foo"]))
        self.assertTrue(tm.matches(["bar"]))
        self.assertFalse(tm.matches(["bar", "something"]))
        self.assertFalse(tm.matches(["something"]))
        self.assertFalse(tm.matches(["something", "foo"]))
        self.assertFalse(tm.matches(["something", "baz"]))

    def test_exclude_tag(self):
        tm = TagMatcher(["1", "!foo"])
        self.assertTrue(tm.matches([]))
        self.assertTrue(tm.matches([""]))
        self.assertTrue(tm.matches(["bar"]))
        self.assertFalse(tm.matches(["foo"]))

    def test_excludetwo_tag(self):
        tm = TagMatcher(["1", "!foo", "!bar"])
        self.assertTrue(tm.matches([]))
        self.assertTrue(tm.matches([""]))
        self.assertTrue(tm.matches(["baz"]))
        self.assertFalse(tm.matches(["bar"]))
        self.assertFalse(tm.matches(["foo"]))

    def test_excludeemptyonly_tag(self):
        tm = TagMatcher(["1", "!"])
        self.assertTrue(tm.matches([]))
        self.assertTrue(tm.matches(["bar"]))
        self.assertTrue(tm.matches(["foo"]))
        self.assertFalse(tm.matches([""]))

    def test_excludeempty_tag(self):
        tm = TagMatcher(["1", "!", "foo", "bar"])
        self.assertTrue(tm.matches([]))
        self.assertTrue(tm.matches(["bar"]))
        self.assertTrue(tm.matches(["foo"]))
        self.assertFalse(tm.matches(["baz"]))
        self.assertFalse(tm.matches([""]))
