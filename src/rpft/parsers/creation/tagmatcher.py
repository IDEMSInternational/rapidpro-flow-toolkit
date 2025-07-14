import collections


class TagMatcher:
    def __init__(self, params=[]):
        self.include_patterns = collections.defaultdict(list)
        self.exclude_patterns = collections.defaultdict(list)
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
                        "Tags parameter must start with a number indicating the tag"
                        " position"
                    )
                if param[0] == "!":
                    self.exclude_patterns[current_index].append(param[1:])
                else:
                    self.include_patterns[current_index].append(param)
                    # Empty string is accepted by default
                    self.include_patterns[current_index].append("")

    def matches(self, tags):
        matches = True
        for i, tag in enumerate(tags):
            if i in self.include_patterns and tag not in self.include_patterns[i]:
                matches = False
            if i in self.exclude_patterns and tag in self.exclude_patterns[i]:
                matches = False
        return matches
