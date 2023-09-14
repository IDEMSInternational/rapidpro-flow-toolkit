from rpft.rapidpro.models.campaigns import Campaign, CampaignEvent
from rpft.logger.logger import get_logger, logging_context

LOGGER = get_logger()


class CampaignParser:
    def __init__(self, name, group_name, rows):
        self.campaign = Campaign(name, group_name=group_name)
        self.rows = rows

    def parse(self):
        for row_idx, row in enumerate(self.rows):
            with logging_context(f"row {row_idx+2}"):
                message = None
                base_language = None
                if row.message:
                    message = {"eng": row.message}
                    base_language = row.base_language or "eng"
                delivery_hour = -1
                if row.delivery_hour:
                    delivery_hour = int(row.delivery_hour)
                try:
                    event = CampaignEvent(
                        int(row.offset),
                        row.unit,
                        row.event_type,
                        delivery_hour,
                        row.start_mode,
                        relative_to_label=row.relative_to,
                        flow_name=row.flow or None,
                        message=message,
                        base_language=base_language,
                    )
                    self.campaign.add_event(event)
                except ValueError as e:
                    LOGGER.critical(str(e))
        return self.campaign
