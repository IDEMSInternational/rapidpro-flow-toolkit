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
    image: str = ""
    audio: str = ""
    video: str = ""
    attachments: List[str] = []


class ChatbotDefinition:
    def __init__(self, flow_definitions, data_sheets, templates, surveys):
        self.flow_definitions = flow_definitions
        self.data_sheets = data_sheets
        self.templates = templates
        self.surveys = surveys

    def get_data_sheet_rows(self, sheet_name):
        return self.data_sheets[sheet_name].rows

    def get_data_sheet_row(self, sheet_name, row_id):
        return self.data_sheets[sheet_name].rows[row_id]

    def get_template(self, name):
        return self.templates[name]
