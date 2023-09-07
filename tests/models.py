from typing import List
from rpft.parsers.common.rowparser import ParserModel


class Condition(ParserModel):
    value: str = ""
    var: str = ""
    type: str = ""
    name: str = ""
    # TODO: We could specify proper default values here, and write custom
    # validators that replace '' with the actual default value.


class FromWrong(ParserModel):
    # 'Wrong' because this doesn't make too much sense:
    # We'd be associating a single edge with multiple conditions.
    # It's still useful for the testcases we have though.
    row_id: str
    conditions: List[Condition]
