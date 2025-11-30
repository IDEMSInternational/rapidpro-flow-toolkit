# The Columns
row_id	type	from	loop_variable	condition	condition_var	condition_type	condition_name	include_if	message_text	save_name	data_sheet	data_row_id	choices.1	choices.2	choices.3	choices.4	choices.5	image	audio	video	obj_name	obj_id	node_name	_nodeId	no_response

# **Row Types Reference**

This document outlines the standard type definitions available in the spreadsheet flow builder.

## **Basic Types**

### **send\_message**

Sends a text message to the user.

* **message\_text**: The content of the message. Supports variable substitution (e.g., Hello {{name}}).  
* **include\_if**: (Optional) A condition that must be true for this message to be sent. Useful for conditional logic without branching.  
* **save\_name**: (Optional) Not typically used for simple messages unless capturing specific states.

### **begin\_for / end\_for**

Used to create loops. See [Loops Documentation](#for-loops) for full details.

## **Logic Columns (Common to all types)**

Most row types support the following logic columns to control execution flow:

### **include\_if**

A boolean expression (e.g., {@age \> 18@}).

* If **True**: The row is executed.  
* If **False**: The row is skipped completely.  
* **Use Case**: Filtering specific messages inside a loop or providing optional information.

### **save\_name**

Saves the result of the current row (if applicable) or a specific value into the bot's memory context.

* Variables saved here can be used in subsequent rows via {{variable\_name}} or {@variable\_name@}.

## **Condition Columns (condition, condition\_var, etc.)**

*Appears in advanced implementations for branching logic.*

* **condition\_var**: The variable being tested (e.g., {@user\_input@}).  
* **condition\_type**: The operator (e.g., has\_any\_word, starts\_with, \=).  
* **condition\_name**: Often maps to a named path or logic gate.  
* **condition**: A legacy or simplified field for direct boolean checks.

*Note: For simple conditional logic, prefer using include\_if on individual rows.*

# For Loops

The begin\_for and end\_for types allow you to iterate over a collection of data (like a list of options or a dataset column) and repeat a set of actions for each item in that collection.

## **Syntax Overview**

A loop consists of three main parts:

1. **Start**: A row with type begin\_for.  
2. **Body**: Any number of rows between the start and end. These are the actions that will be repeated.  
3. **End**: A row with type end\_for.

### **Example**

The following example demonstrates how to iterate over a list stored in the variable column\_id. For each item, it sends a message displaying the index and the value.

| row\_id | type | loop\_variable | include\_if | message\_text |
| :---- | :---- | :---- | :---- | :---- |
|  | send\_message |  |  | Selection options: |
|  | begin\_for | msg;i |  | {@column\_id@} |
|  | send\_message |  | {@msg\!=""@} | {{i}}: {{msg}} |
|  | end\_for |  |  |  |

## **Column Definitions**

When using begin\_for, the columns behave slightly differently than standard message rows:

### **type**

* **begin\_for**: Marks the start of the loop block.  
* **end\_for**: Marks the end of the loop block.

### **message\_text (The Iterable)**

On the begin\_for row, the message\_text column is used to define **what you are looping over**.

* This should be a reference to an array or object (e.g., {@column\_id@}).

### **loop\_variable (Iterator & Index)**

Defines the variable names available inside the loop context. You can define just the value, or both the value and the index, separated by a semicolon ;.

* **Format**: value\_name;index\_name  
* **Example**: msg;i  
  * msg: Becomes the variable for the current item in the list.  
  * i: Becomes the variable for the current index number (0, 1, 2...).
* See [Advanced For Loops](#advanced-for-loops) for options using lists and dicts of column IDs

## **Detailed Behavior**

1. **Initialization**: When the bot hits begin\_for, it evaluates the expression in message\_text to get a list.  
2. **Iteration**:  
   * It assigns the first item to your loop\_variable (e.g., msg).  
   * It executes all rows between begin\_for and end\_for.  
   * In the example above, the inner send\_message uses {{i}} and {{msg}} to print the current item.  
3. **Termination**: Once all items have been processed, the flow continues to the row immediately following end\_for.

### **Filtering inside loops**

You can use standard logic columns like include\_if within the loop to skip specific items. In the example above, {@msg\!=""@} ensures that empty options are not displayed to the user.

### Advanced For Loops

In addition to iterating over column IDs, for loops can iterate over rows producing lists or dicts.

#### Lists

#### Dicts

Dicts are a strange one, if you provide a straight dict, e.g. `{@{'title': title, 'msg': msg, 'points': points}@}` it will only iterate over the keys. However, it works if you wrap the dict in a list:

| row\_id | type | loop\_variable | include\_if | message\_text |
| :---- | :---- | :---- | :---- | :---- |
|  | send\_message |  |  | Selection options: |
|  | begin\_for | row;i |  | {@[{'title': title, 'msg': msg, 'points': points}]@} |
|  | send\_message |  |  | {{row['title']}}: {{row['points']}} points \n {{row['msg']}}  |
|  | end\_for |  |  |  |

#### Arguments

In the content index, it is possible to pass in a data list as an argument, as some arbitrarily defined argument varible. For this case we consider an argument called `arg`

`content_index`:
| type                | sheet_name  | data_sheet | data_row_id | new_name | data_model | template_arguments                                           |
|---------------------|-------------|------------|-------------|----------|------------|--------------------------------------------------------------|
| template_definition | select_list |            |             |          |            | arg;sheet\|                                       |
| data_sheet          | task_list   |            |             |          |            |                                                              |
| create_flow         | select_list |            |             |          |            | task_list |


| row\_id | type | loop\_variable | include\_if | message\_text |
| :---- | :---- | :---- | :---- | :---- |
|  | send\_message |  |  | Selection options: |
|  | begin\_for | arg;i |  | {@arg.values()@} |
|  | send\_message |  |  | {{arg.title}}: {{arg.points}} points; {{arg.msg}}  |
|  | end\_for |  |  |  |
