import logging

from rpft.logger.logger import logging_context
from rpft.rapidpro.models.triggers import Trigger


LOGGER = logging.getLogger(__name__)


class TriggerParser:
    def __init__(self, sheet_name, rows):
        self.sheet_name = sheet_name
        self.rows = rows

    def parse(self):
        triggers = []
        for row_idx, row in enumerate(self.rows):
            with logging_context(f"row {row_idx+2}"):
                try:
                    trigger = Trigger(
                        row.type,
                        row.keywords,
                        row.channel,
                        row.match_type,
                        flow_name=row.flow,
                        group_names=row.groups,
                        group_uuids=[],
                        exclude_group_names=row.exclude_groups,
                        exclude_group_uuids=[],
                    )
                    triggers.append(trigger)
                except ValueError as e:
                    raise Exception(str(e))
        return triggers
