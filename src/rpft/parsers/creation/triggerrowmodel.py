from typing import List

from pydantic import validator

from rpft.parsers.common.rowparser import ParserModel


class TriggerRowModel(ParserModel):
    type: str  # K (keyword) or C (uncaught) or M (missed call)
    keyword: str = ""
    flow: str = ""
    groups: List[str] = []
    channel: str = ""

    @validator("type")
    def validate_unit(cls, v):
        if v not in ["K", "C", "M"]:
            raise ValueError(
                'type must be "K" (keyword), ' '"C" (uncaught), or "M" (missed call)'
            )
        return v
