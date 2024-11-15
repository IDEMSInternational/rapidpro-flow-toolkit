from typing import List

from rpft.parsers.common.rowparser import ParserModel


class Condition(ParserModel):
    # Value to check against. (Does not support checks with a list of values)
    value: str = ""
    # Variable or expression that is being checked against value
    variable: str = ""
    # Type of the conditional check, e.g. has_any_word (default)
    type: str = ""
    # Name -- only for display in RapidPro
    name: str = ""


class ConditionWithMessage(ParserModel):
    condition: Condition
    message: str


class ConditionsWithMessage(ParserModel):
    conditions: List[ConditionWithMessage] = []
    general_message: str = ""


class Assignment(ParserModel):
    # Assign a value to a variable
    variable: str
    value: str


class Expiration(ParserModel):
    # Time after which a flow expires
    time: str = ""
    # Message to send when the flow expires
    message: str = ""


class Message(ParserModel):
    text: str
    attachment: str = ""
