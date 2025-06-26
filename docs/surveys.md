# Surveys

Surveys can be created by defining a data sheet of questions, indexing it in the content index and adding a `survey` row in the content index.

A basic usage example can be found in `TestSurveyParser.test_basic_survey` in `tests/test_surveyparser.py`.

It is also possible to create an individual question by adding a `survey_question` row to the content index.


## The question data sheet

Each survey consist of questions. Questions have an underlying data model `SurveyQuestionRowModel`. This consists of the fields defined in `SurveyQuestionModel` in `src/rpft/parsers/creation/surveymodels.py` and an additional `ID` field.

Each question consists of the question text, an associated variable that the user input is stored in, and a variety of other fields.

### Basic question fields

These are the basic fields of a question definition (can be used as column headers for question data sheets).

- `ID`: Identifier, used for flow and variable name generation.
- `type`: Question type. Pre-defined types include `text`, `mcq`, ..., but custom ones can be used if the specific templates are defined by the user.
- `messages`: The question text. This is a list of multiple messages, each message having a `text` and optional `image`/`audio`/`video` attachment fields, as well as a list `attachments` of generic attachments.
	- `question`: Shorthand for `messages.1.text`; you may use this instead of `messages` if none of your questions send more than 1 message.
	- `attachment`: Shorthand for `messages.1.attachment`; you may use this instead of `messages` if none of your questions send more than 1 message.
	- Note that these shorthands can NOT be used within template definitions.
- `variable`: Variable to store the user input in. If blank, generated from the question ID as `sq_{survey_id}_{question_id}`. The survey_id/question_id is the survey's name/question ID, **in all lowercase with non-alphanumeric characters removed**
- `completion_variable`: Variable indicating whether question has been completed. If blank, generated from the variable as `{variable}_complete`
- `choices`: For multiple choice questions: a list of choices
- `expiration.message`: Message that gets sent when the user doesn't respond in a long time
- `expiration.time`: [not implemented]

It is possible to reuse questions across multiple surveys (see `tags` below). In that case, we need to make sure that each copy of a question gets a unique name for its variables. Auto-generating the variable names from the question ID solves the question of creating unique variable names, however, we also need a way to refer to these variable names independent of the `surveyid` which is used for this.

Therefore we have the following shorthands, which can be used within any field of a question:

- `@answer` is short for `@fields.{variable}`. This is useful even without reusing questions, e.g. within confirmation/validation/stop conditions (see below).
- `@answerid` is short for `{variable}`. This can be used when defining new variables (in postprocessing steps) whose names should depend on the variable in the question.
- `@prefix` is short for `@fields.sq_{survey_id}`. This is useful when referencing variables from previous questions of the survey, by using e.g. `@prefix_{prev_question_id}`
- `@prefixid` is short for `sq_{survey_id}`. Similar to above
- `@surveyid` is short for the survey ID (`{survey-id}`)
- `@questionid` is short for the question ID (`{question_id}`)


### Special question fields

These are the more complex fields of a question definition (can be used as column headers for question data sheets).

#### `tags`: Tags for filtering

Data sheets can be created by filtering an existing data sheet by a condition (e.g. `'my_tag' in tags`), so that only rows fulfilling the condition are included. This way, the same pool of questions can be used for multiple surveys, by selecting questions via a survey-specific tag.

#### `relevant`: Omit a question based on previous answers

If any of the given conditions does not hold, skip the question. These conditions will commonly depend on previous answers.

#### `confirmation`: Conditional Answer confirmation

If one of the conditions holds, print the confirmation message associated with that condition, with options Yes/No. If user enters No, repeat the question.

Example:

- Do you confirm that you're under 18? [if @answer < 18]
- Please confirm your input @answer [Unconditional confirmation can be realized by specifying a condition that is always true]

#### `stop`: Conditional premature end of survey (later: forward skip?)

If one of the conditions holds, send the message associated with the condition and end the survey.

Example:

- user's age is less than 18
- user is not a parent
- user does not live in the target region

#### `validation`: Validation / conditional repetition of question

If one of the conditions holds, send the message associated with the condition and repeat the question.

Example:

- Your name is too short. Please enter again.

#### `postprocessing`: Variable postprocessing

Postprocessing to do after a user's answer is successfully stored. This could be an assignment (of the same or another variable), or a flow that is triggered.

Examples:

- take the user's entered name and capitalize it (stored in the same variable)
- create a new age_bucket variable based on the user's age input. If the age variable is called `sq_sid_age`, specifying the new variable in the assignment to be `@answerid_bucket` with create a variable `sq_sid_age_bucket`

#### `skipoption`: Optional questions

A way for the user to skip the question by typing in a specific phrase.

## Content index rows

After creating a data sheet with questions, in the content index, you can create a row of type `data_sheet` and specify the `data_model` as `SurveyQuestionRowModel`. This is a global model that does not need to be defined by the user in a custom module.

Then, create a row of type `survey`. For this, the following columns are relevant:

- `data_sheet`: A data sheet with questions
- `new_name`: Name of the survey. If not provided, the name of the `data_sheet` is used.
- `config`: A SurveyConfig object, see `src/rpft/parsers/creation/surveymodels.py`. May become deprecated in the future.
    - `variable_prefix`: Prefix to apply to all RapidPro variables that are created by the survey. For each `SurveyQuestion`, this is the `variable`, `completion_variable` and `postprocessing.assignments.*.variable`. Ideally, avoid this feature in favor of using auto-generated variable names, `@answer`, `@answerid` and `@prefix`.
    - `expiration_message`: Message to send when a question flow expires. If a question does not specify an expiration message, this message is used by default. Ideally, avoid this feature in favor of using template_arguments.
- `template arguments`: Template arguments to be passed down to the survey template `template_survey_wrapper`. These arguments are also passed down to the template `template_survey_question_wrapper`. Other templates that are included as blocks within these two templates naturally have access to these template arguments as well.

This will create one flow for each question, named `survey - {survey name} - question - {question ID}`, as well as a survey flow `survey - {survey name}` that invokes each question via `start_new_flow`. This is achieved via templating. The templates can be customized if needed.

### Individual questions

Individual questions can be created through a row of type `survey_question`. For this, the following columns are relevant:

- `data_sheet`: A data sheet with questions
- `data_row_id`: The value of the ID column in the row of `data_sheet` that shall be used to create the question (question ID).
- `new_name`: Name of the survey (survey name). If not provided, the name of the `data_sheet` is used.
- `template arguments`: Template arguments to be passed down to the template `template_survey_question_wrapper`. Other templates that are included as blocks within this templates naturally have access to these template arguments as well.

This will create one flow, named `survey - {survey name} - question - {question ID}`.

Note: Unlike surveys, the `config` column (SurveyConfig) is ignored.

## Survey templates

We define global templates that are used by surveys. These templates can be found in `src/rpft/parsers/creation/survey_templates/`. They are as follows:

- `template_survey_wrapper`: Flow rendering all the questions.
	- Receives the following context variables that can be used in the template:
		- `questions`: a list of `SurveyQuestionRowModel`
		- `survey_name`: Name of the survey
		- `survey_id`: ID of the survey (generated from name)
	- In the content index, a `survey` row can have `template_arguments`. If present, these are passed to the `template_survey_wrapper` template when creating a survey.
- `template_survey_question_wrapper`: Question functionality that is common to all input types. Invoked by the survey via `start_new_flow`
	- Receives the fields of the `SurveyQuestionRowModel` as its context variables
	- Currently, it is not possible to pass template arguments to this template.
- `template_survey_question_block_{type}`: For each question input type `{type}`, there is a template to read the user data. These are included into the `template_survey_question_wrapper` via `insert_as_block`
	- Because this template is inserted as a block, any context that is available in `template_survey_question_wrapper` (in particular, `question`) is also available in this template.

The user can overwrite these by defining a template of the same name in the content index, thereby using their own custom templates. There is no constraint on what `{type}` can be, therefore the user can also create their own question types.
