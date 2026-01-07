# Error types:

## No step in

The old simulator did not step into flows and evaluate them, only showed where each flow would go

The rpft simulator doesn't actually step into the flows, it only evaluates when flows are entered. 

**Proposed Fix:**
If we want to match that output, flowrunner would allow us to, but we'd just need to make another thing to parse the message strings to an array we can compare to (or we could just do direct string match).
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

## Expected flows malformed

The expected flows from `all_test_flows.json` are malformed and do not load into RapidPro
**Proposed Fix:**
Reexport all flows

## Setting a field for the second time does not produce an event

When setting a field, e.g. setting `@fields.favorite_numbers` to 3, an event is only created if `@fields.favorite_numbers` is not already 3.
This leads to a mismatch between the rpft sims expected result [('set_contact_field', 'favourite_number'), ('set_contact_field', 'favourite_number')], and the flowrunner/rapidpro events [('set_contact_field', 'favourite_number')]

**Proposed Fix:**
Smarter matching, ignore those cases? Create a loop test case that actually changes the field each time?

## Unable to read

Null uuids are unallowed, in actions and elsewhere

## Inconsistant recording of events
Inconsistant recording ofrun results, contact language changes, etc. Some tests want `set_run_result` events to be reported, others do not.

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

## tests.test_flowparser.TestFlowParser

### test_switch_nodes (tests.test_flowparser.TestFlowParser.test_switch_nodes)

unable to read

### test_loop_from_start (tests.test_flowparser.TestFlowParser.test_loop_from_start)

Setting a field for the second time does not produce an event

### test_no_switch_nodes (tests.test_flowparser.TestFlowParser.test_no_switch_nodes)

Inconsistant recording of events

### test_no_switch_nodes_without_row_ids (tests.test_flowparser.TestFlowParser.test_no_switch_nodes_without_row_ids) [Flowrunner Equivalence no_switch_nodes: expected]

Inconsistent recording of events

## tests.test_flowparser.TestMultiExitBlocks

There is one case where the flows are unable to be read, the rest of the test cases fail because the field named `@my_field` should be renamed to be a valid variable like `@fields.my_field`

### test_enter_flow (tests.test_flowparser.TestMultiExitBlocks.test_enter_flow)

unable to read

## tests.test_flowparser.TestWebhook

There is something hacky going on here with the inputs somehow triggering whether or not the simulator thinks the webhook succeded. This isn't able to be replicated in flowrunner directly. Possibly we should look into a real webhook endpoint to verify success, and point it at a known bad endpoint to verify failure.

<!-- Completed
## tests.test_flowparser.TestNoOpRow

### test_multiexit_noop

Bad variable name `@field`

### test_multiexit_noop2

Bad variable name `@field`

### test_multientryexit_noop
Bad variable name `@field`

### test_noop_in_block2
Bad variable name `@field` -->