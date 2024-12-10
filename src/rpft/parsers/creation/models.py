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


class TemplateSheet:
    def __init__(self, name, table, argument_definitions):
        self.name = name
        self.table = table
        self.argument_definitions = argument_definitions


class ChatbotDefinition:
    def __init__(
        self,
        flow_definitions,
        data_sheets,
        templates: List[TemplateSheet],
        surveys,
    ):
        self.flow_definitions = flow_definitions
        self.data_sheets = data_sheets
        self.templates = templates
        self.surveys = surveys

    def get_data_sheet_rows(self, sheet_name):
        return self.data_sheets[sheet_name].rows

    def get_data_sheet_row(self, sheet_name, row_id):
        return self.data_sheets[sheet_name].rows[row_id]

    def get_template(self, name) -> TemplateSheet:
        return self.templates[name]


class SurveyConfig(ParserModel):
    # Prefix to apply to all variable names in the survey
    variable_prefix: str = ""
    # Message to send when a question flow expires
    expiration_message: str = ""


class MCQChoice(ParserModel):
    # Text rendered to user
    text: str
    # Text stored in survey variable
    value: str


class PostProcessing(ParserModel):
    # Assignments to perform via save_value rows
    assignments: List[Assignment] = []
    # flow to invoke for postprocessing
    flow: str = ""


class SkipOption(ParserModel):
    # The text with instructions that the user sees
    text: str = ""
    # The Choice (quick reply/text) the user has to enter to skip this question
    choice: str = ""
    # The value that is stored in the question variable if the question is skipped
    value: str = ""


class SurveyQuestionModel(ParserModel):
    # type of the question
    type: str
    # question text
    messages: List[Message]
    # Variable to store the user input in
    # If blank, generated from the question ID as sq_{survey_id}_{question_id}
    # The survey_id/question_id is the survey's name/question's ID
    # in all lowercase with non-alphanumeric characters removed
    variable: str = ""
    # Variable indicating whether question has been completed
    # If blank, generated from the question ID as {variable}_complete
    completion_variable: str = ""
    # MCQ specific fields
    choices: List[MCQChoice] = []

    # Message to send when question flow expires
    # If blank, message from survey configuration is used
    expiration: Expiration = Expiration()
    # Conditions required to present the question, otherwise skipped.
    relevant: List[Condition] = []
    ## Make question skippable
    # Adds an additional choice allowing use to skip the question.
    skipoption: SkipOption = SkipOption()
    ## Conditional Answer confirmation
    # Condition for sending a message asking the user to confirm their answer
    # Comes with a Yes/No choice for the user.
    # No repeats the question, Yes stores the answer and proceeds.
    confirmation: ConditionsWithMessage = ConditionsWithMessage()
    ## Conditional premature end of survey (later: forward skip?)
    # Condition that ends the survey (with message to user)
    stop: ConditionsWithMessage = ConditionsWithMessage()
    ## Validation / conditional repetition of question
    # If condition holds, message is printed and question is repeated.
    validation: ConditionsWithMessage = ConditionsWithMessage()
    ## Variable postprocessing
    # Postprocessing to do after a user's answer is successfully stored
    # This could be an assignment (of the same or another variable),
    # Or a flow that is triggered.
    postprocessing: PostProcessing = PostProcessing()
    # tags allowing to filter questions to appear in a survey
    tags: List[str] = []

    def header_name_to_field_name_with_context(header, row):
        if header == "question":
            return "messages.1.text"
        elif header == "image":
            return "messages.1.image"
        else:
            return header
