from pydantic import field_validator

from rpft.parsers.common.rowparser import ParserModel


class CampaignEventRowModel(ParserModel):
    uuid: str = ""
    offset: int
    unit: str
    event_type: str
    delivery_hour: str = ""
    message: str = ""
    relative_to: str
    start_mode: str
    flow: str = ""
    base_language: str = ""

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v):
        if v not in ["M", "H", "D", "W"]:
            raise ValueError("unit must be M (minute), H (hour), D (day) or W (week)")
        return v

    @field_validator("start_mode")
    @classmethod
    def validate_start_mode(cls, v):
        if v not in ["I", "S", "P"]:
            raise ValueError(
                "start_mode must be I (interrupt current flow), S (skip event if in"
                " flow) or P (send message and don't affect flow)"
            )
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v):
        if v not in ["M", "F"]:
            raise ValueError("event_type must be F (flow) or M (message)")
        return v
