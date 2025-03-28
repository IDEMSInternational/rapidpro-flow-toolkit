import logging

from rpft.parsers.creation.models import TemplateSheet


LOGGER = logging.getLogger(__name__)


def map_template_arguments(template: TemplateSheet, args, context, data_sheets) -> dict:
    """
    Map template arguments, which are positional, to the arguments from the template
    definition, and add the values of the arguments to the context with the appropriate
    variable name (from the definition).
    """
    arg_defs = template.argument_definitions

    if arg_defs and len(args) > len(arg_defs):
        # Once the row parser is cleaned up to eliminate trailing '' entries, this
        # won't be necessary
        extra_args = args[len(arg_defs) :]
        non_empty_extra_args = [ea for ea in extra_args if ea]

        if non_empty_extra_args:
            LOGGER.warning(
                "Too many template arguments provided, "
                + str(
                    {
                        "template": template.name,
                        "extra": non_empty_extra_args,
                        "definition": arg_defs,
                        "arguments": args,
                    }
                )
            )

        args = args[: len(arg_defs)]

    args_padding = [""] * (len(arg_defs) - len(args))

    for arg_def, arg in zip(arg_defs, args + args_padding):
        value = arg if arg != "" else arg_def.default_value

        if value == "":
            raise Exception(f'Required template argument "{arg_def.name}" not provided')

        value = data_sheets[value].rows if arg_def.type == "sheet" else value

        if arg_def.name in context and value != context[arg_def.name]:
            LOGGER.warn(
                "Template argument reassigned, "
                + str(
                    {
                        "template": template.name,
                        "name": arg_def.name,
                        "before": context[arg_def.name],
                        "after": value,
                    }
                )
            )

        context[arg_def.name] = value

    return context
