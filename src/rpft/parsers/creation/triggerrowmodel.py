from typing import List

from pydantic import validator

from rpft.parsers.common.rowparser import ParserModel


class TriggerRowModel(ParserModel):
    type: str
    keywords: List[str] = ""
    flow: str = ""
    groups: List[str] = []
    exclude_groups: List[str] = []
    channel: str = ""
    match_type: str = ""

    @validator("type")
    def validate_type(cls, v):
        if v not in ["K", "C", "M", "T"]:
            raise ValueError(
                'type must be "K" (keyword), "C" (uncaught), '
                '"T" (ticket), or "M" (missed call)'
            )
        return v

    @validator("match_type")
    def validate_match_type(cls, v, values):
        if values["type"] == "K" and v not in ["F", "O", ""]:
            raise ValueError(
                'match_type must be "F" (starts with) or "O" (only) if type is "K".'
            )
        return v
