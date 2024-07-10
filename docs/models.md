# Models

## Automatic model inference

Models of sheets can now be automatically inferred if no explicit model is provided.

This is done exclusively by parsing the header row of a sheet. Headers can be annotated with types (basic types and list; dict and existing models are currently not supported). If no annotation is present, the column is assumed to be a string.

Examples of what the data in a column can represent:
- `field`: `field` is inferred to be a string
- `field:int`: `field` is inferred to be a int
- `field:list`: `field` is inferred to be a list
- `field:List[int]`: `field` is inferred to be a list of integers
- `field.1`: `field` is inferred to be a list, and this column contains its first entry
- `field.1:int`: `field` is inferred to be a list of integers, and this column contains its first entry
- `field.subfield`: `field` is inferred to be another model with one or multiple subfields, and this column contains values for the `subfield` subfield
- `field.subfield:int`: `field` is inferred to be another model with one or multiple subfields, and this column contains values for the `subfield` subfield which is inferred to be an integer
- `field.1.subfield`: `field` is inferred to be a list of another model with one or multiple subfields, and this column contains values for the `subfield` subfield of the first list entry

Intermediate models like in the last three examples are created automatically.
