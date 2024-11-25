from rpft.logger.logger import get_logger

LOGGER = get_logger()


def map_template_arguments(arg_defs, args, context, data_sheets) -> dict:
    """
    Map template arguments, which are positional, to the arguments from the template
    definition, and add the values of the arguments to the context with the appropriate
    variable name (from the definition).
    """
    if len(args) > len(arg_defs):
        # Once the row parser is cleaned up to eliminate trailing '' entries, this
        # won't be necessary
        extra_args = args[len(arg_defs) :]
        non_empty_extra_args = [ea for ea in extra_args if ea]

        if non_empty_extra_args:
            LOGGER.warning("Too many arguments provided to template")

        args = args[: len(arg_defs)]

    args_padding = [""] * (len(arg_defs) - len(args))

    for arg_def, arg in zip(arg_defs, args + args_padding):
        if arg_def.name in context:
            LOGGER.critical(
                f'Template argument "{arg_def.name}" doubly defined '
                f'in context: "{context}"'
            )

        arg_value = arg if arg != "" else arg_def.default_value

        if arg_value == "":
            LOGGER.critical(
                f'Required template argument "{arg_def.name}" not provided'
            )

        context[arg_def.name] = (
            data_sheets[arg_value].rows
            if arg_def.type == "sheet"
            else arg_value
        )

    return context
