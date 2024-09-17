from pydantic import field_validator, model_validator

from rpft.parsers.common.rowparser import ParserModel


class TriggerRowModel(ParserModel):
    type: str
    keywords: list[str] = []
    flow: str = ""
    groups: list[str] = []
    exclude_groups: list[str] = []
    channel: str = ""
    match_type: str = ""

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ["K", "C", "M", "T"]:
            raise ValueError(
                'type must be "K" (keyword), "C" (uncaught), '
                '"T" (ticket), or "M" (missed call)'
            )
        return v

    @model_validator(mode="after")
    def validate_match_type(self):
        if self.type == "K" and self.match_type not in ["F", "O", ""]:
            raise ValueError(
                'match_type must be "F" (starts with) or "O" (only) if type is "K".'
            )

        return self
