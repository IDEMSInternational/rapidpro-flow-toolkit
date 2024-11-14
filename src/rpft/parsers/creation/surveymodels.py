from typing import List

from rpft.parsers.common.rowparser import ParserModel
from rpft.parsers.creation.commonmodels import (
    Assignment,
    Condition,
    ConditionsWithMessage,
)


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
    type: str
    # question text
    question: str
    # Variable to store the user input in
    variable: str = ""
    # Variable indicating whether question has been completed
    # If blank, generated from the question ID
    completion_variable: str = ""
    # Conditions required to present the question, otherwise skipped.
    # If blank, generated from the question ID
    relevant: List[Condition] = []
    # Message to send when question flow expires
    # If blank, message from survey configuration is used
    expiration_message: str = ""
    # MCQ specific fields
    choices: List[MCQChoice] = []
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
