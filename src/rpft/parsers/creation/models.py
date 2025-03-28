from rpft.parsers.common.rowparser import ParserModel


class Condition(ParserModel):
    value: str = ""
    """
    Value to check against. (Does not support checks with a list of values).
    """

    variable: str = ""
    """
    Variable or expression that is being checked against value.
    """

    type: str = ""
    """
    Type of the conditional check, e.g. has_any_word (default).
    """

    name: str = ""
    """
    Display name in RapidPro only.
    """


class ConditionWithMessage(ParserModel):
    condition: Condition
    message: str


class ConditionsWithMessage(ParserModel):
    conditions: list[ConditionWithMessage] = []
    general_message: str = ""


class Assignment(ParserModel):
    """
    Assign a value to a variable
    """

    variable: str
    value: str


class Expiration(ParserModel):
    time: str = ""
    """
    Time after which a flow expires.
    """

    message: str = ""
    """
    Message to send when the flow expires.
    """


class Message(ParserModel):
    text: str
    image: str = ""
    audio: str = ""
    video: str = ""
    attachments: list[str] = []


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
        templates: list[TemplateSheet],
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
    variable_prefix: str = ""
    """
    Prefix to apply to all variable names in the survey.
    """

    expiration_message: str = ""
    """
    Message to send when a question flow expires.
    """


class MCQChoice(ParserModel):
    text: str
    """
    Text rendered to user.
    """

    value: str
    """
    Text stored in survey variable.
    """


class PostProcessing(ParserModel):
    assignments: list[Assignment] = []
    """
    Assignments to perform via save_value rows.
    """

    flow: str = ""
    """
    Flow to invoke for postprocessing.
    """


class SkipOption(ParserModel):
    text: str = ""
    """
    The text with instructions that the user sees.
    """

    choice: str = ""
    """
    The choice (quick reply/text) the user has to enter to skip this question.
    """

    value: str = ""
    """
    The value that is stored in the question variable if the question is skipped.
    """

class Confirmation(ParserModel):
    condition: Condition = Condition()
    question: str = ""
    confirm_option: str = ""
    back_option: str = ""


class SurveyQuestionModel(ParserModel):
    """
    Representation of a survey question.
    """

    type: str
    """
    Type of the question.
    """

    messages: list[Message]
    """
    Question text.
    """

    variable: str = ""
    """
    Variable to store the user input in. If blank, generated from the question ID as
    sq_{survey_id}_{question_id}. The survey_id/question_id is the survey's
    name/question's ID in all lowercase with non-alphanumeric characters removed.
    """

    completion_variable: str = ""
    """
    Variable indicating whether question has been completed. If blank, generated from
    the question ID as {variable}_complete.
    """

    choices: list[MCQChoice] = []
    """
    MCQ specific fields.
    """

    expiration: Expiration = Expiration()
    """
    Message to send when question flow expires. If blank, message from survey
    configuration is used.
    """

    relevant: list[Condition] = []
    """
    Conditions required to present the question, otherwise skipped.
    """

    skipoption: SkipOption = SkipOption()
    """
    Make question skippable. Adds an additional choice allowing user to skip the
    question.
    """

    # confirmation: ConditionsWithMessage = ConditionsWithMessage()
    confirmation: Confirmation = Confirmation()
    """
    Conditional Answer confirmation. If a condition holds, send a message asking the
    user to confirm their answer. Comes with a Yes/No choice for the user.
    'No' repeats the question; 'Yes' stores the answer and proceeds.
    """

    stop: ConditionsWithMessage = ConditionsWithMessage()
    """
    Conditional premature end of survey (later: forward skip?).
    If ANY of the conditions hold, ends the survey (with message to user).
    """

    validation: ConditionsWithMessage = ConditionsWithMessage()
    """
    Validation / conditional repetition of question. If a condition holds,
    its associated message is printed and the question is repeated.
    """

    postprocessing: PostProcessing = PostProcessing()
    """
    Variable postprocessing. Postprocessing to do after a user's answer is successfully
    stored. This could be an assignment (of the same or another variable), or a flow
    that is triggered.
    """

    tags: list[str] = []
    """
    Tags allowing to filter questions to appear in a survey.
    """

    def header_name_to_field_name_with_context(header, row):
        if header == "question":
            return "messages.1.text"
        elif header == "image":
            return "messages.1.image"
        else:
            return header
