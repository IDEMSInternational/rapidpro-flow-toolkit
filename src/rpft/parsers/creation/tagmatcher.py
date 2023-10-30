import collections


class TagMatcher:
    def __init__(self, params=[]):
        self.tag_patterns = collections.defaultdict(list)
        if not params:
            return
        current_index = None
        for param in params:
            try:
                val = int(param) - 1
            except ValueError:
                val = None
            if val is not None:
                current_index = val
            else:
                if current_index is None:
                    raise ValueError(
                        "Tags parameter must start with a "
                        "number indicating the tag position."
                    )
                self.tag_patterns[current_index].append(param)

    def matches(self, tags):
        matches = True
        for i, tag in enumerate(tags):
            if tag and i in self.tag_patterns and tag not in self.tag_patterns[i]:
                matches = False
        return matches
