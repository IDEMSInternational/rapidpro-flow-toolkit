# Error types:

## No step in

The old simulator did not step into flows and evaluate them, only showed where each flow would go

The rpft simulator doesn't actually step into the flows, it only evaluates when flows are entered. If we want to match that output, flowrunner would allow us to, but we'd just need to make another thing to parse the message strings to an array we can compare to (or we could just do direct string match).
For example we could capture...
```
↪️ entered flow 'survey - Survey Name'

↪️ entered flow 'survey - Survey Name - question - first'

↪️ exited flow 'survey - Survey Name - question - first'
...
```
to more closely align with

```py
[('enter_flow', 'survey - Survey Name - question - first'), ('enter_flow', 'survey - Survey Name - question - second'), ('send_msg', 'You waited too long'), ('set_run_result', 'expired')] 
```
instead of the current parsing of:
```py
[('set_run_result', 'dummy'), ('send_msg', 'First question?'), ('set_contact_field', 'first'), ('set_contact_field', 'first_complete'), ('set_run_result', 'dummy'), ('send_msg', 'Second question?')]
```

## Object has no property

Flowrunner is particular about variable names being correct. In many cases, the existing tests try to use/set things like `my_field.name` or `field.name` when what would work in RapidPro is e.g. `fields.name`. In other cases it is just a single word, or trying to access results variables that have been set to other variable names.

The output from flowrunner (very similar to the behaviour of the simulator in RapidPro)
```
⚠️ error calling test has_any_word(...): error calling has_any_word(...): object has no property 'stop'

⚠️ object has no property 'stop'
```

# Errors

## TestSurveyParser
### test_basic_survey (tests.test_surveyparser.TestSurveyParser.test_basic_survey)

Two errors
1. The input `expired` doesn't force the flow to expire.
2. No Step In


### test_stop_condition (tests.test_surveyparser.TestSurveyParser.test_stop_condition)

Object has no property

```
⚠️ error calling test has_any_word(...): error calling has_any_word(...): object has no property 'stop'

⚠️ object has no property 'stop'
```

### test_template_arguments (tests.test_surveyparser.TestSurveyParser.test_template_arguments)
No Step In

### test_template_overwrite (tests.test_surveyparser.TestSurveyParser.test_template_overwrite)

No Step In