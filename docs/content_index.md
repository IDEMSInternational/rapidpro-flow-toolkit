## template_arguments

Defines arguments that can be used within the template.

When you load a datalist into a basic "for loop print column x" template, it will create a new flow for each of the rows in the datalist, each with one node sending the value of the column for that row. However, if you want to create one flow that sends the column values for each of the rows, you need to use template_arguments.

You can define arguments with the name and type, e.g. `nameA;typeA|nameB;typeB|`

The allowable types are:
- `sheet`
- ??

### Example: Passing formatting strings

A common desired use case is the customization of a message. Suppose we have the datalist:

| id | title | msg | points |
|--|--|--|--|
| 1 | Basic Greeting | Say "Hi" | 10 |
| 2 | Fancy Greeting | Say "Good day to you!" | 30 |

and in one deployment we wanted each of the messages to be output like:

> Basic Greeting | Points: 10 | Task: Say "Hi"

and for another we wanted it to output like
> Basic Greeting | 10 points  
> Say "Hi"

To achive this, we use standard python string.format syntax.

In the content_index, define a template_argument of `parse_str` for the template, then when using create flows you can pass
`"{val.title} | Points: {val.points} | Task: {val.msg}"`, or `"{val.title} | {val.points} points \n{val.msg}"` 

In the loop/template, you then use: `{{parse_str.format(val=val)}}`

#### Reasoning behind this approach
We could simply pass a formatting string like `{{val.title}} | Points: {{val.points}} | Task: {{val.msg}}`, or `{{val.title}} | {{val.points}} points \n{{val.msg}}` respectively.  
**The first pitfall**: That will be parsed at the top level, when the content_index is read, and thus the variables will all be replaced by "" and it won't work.

Thus we need to wrap the jinja template inside of another template, e.g. `{{ '{{val.title}} | Points: {{val.points}} | Task: {{val.msg}}' }}`.  
**The second pitfall** as jinja is a one-shot parser, when `{{parse_str}}` is rendered, it will just be the string, as it does not recursively render variables.

If it did recursively render variables, this approach of wrapping in another template still wouldn't work, as we'd fall back into the first pitfall.

Thus, we must use the python string.format syntax.