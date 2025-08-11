import re


class Context(object):
    def __init__(
        self, group_names=None, inputs=None, random_choices=None, variables=None
    ):
        if group_names is not None:
            self.group_names = group_names
        else:
            self.group_names = []

        if inputs is not None:
            self.inputs = inputs
        else:
            self.inputs = []

        if random_choices is not None:
            self.random_choices = random_choices
        else:
            self.random_choices = []

        if variables is not None:
            self.variables = variables
        else:
            self.variables = dict()


def find_node_by_uuid(flow, node_uuid):
    """Given a node uuid, finds the corresponding node.

    Args:
        flow: flow to search in
        node_uuid: node to search for

    Returns:
        node with uuid matchign node_uuid
        None if no node was found.
    """

    for node in flow["nodes"]:
        if node["uuid"] == node_uuid:
            return node
    return None


def find_destination_uuid(current_node, context):
    """
    For a given node, find the next node that is visited and return its uuid.

    The groups the user is in may affect the outcome.

    Args:
        current_node:
        group_names (`list` of `str`): groups the user is in

    Returns:
        uuid of the node visited after this node.
        Maybe be None if it is the last node.
    """

    # By default, choose the first exit.
    destination_uuid = current_node["exits"][0].get("destination_uuid", None)
    if "router" in current_node:
        router = current_node["router"]
        if router["type"] == "switch":
            # Get value of the operand
            if router["operand"] == "@contact.groups":
                operand = context.group_names
            elif router["operand"] == "@input.text" or current_node["actions"]:
                # Actions implies CallWebhook, TransferAirtime or EnterFlow
                operand = context.inputs.pop(0)
            elif router["operand"] in context.variables:
                operand = context.variables[router["operand"]]
            else:
                operand = None

            # Find the case that applies here and get its category_uuid
            # The arguments are not parse (e.g. no variable substitution)
            category_uuid = router[
                "default_category_uuid"
            ]  # The "Other" option (default)
            if operand is None:
                # Input "None" indicates No Response if the router has a wait.
                if "wait" in router:
                    if (
                        "timeout" in router["wait"]
                        and router["wait"]["timeout"]["seconds"] > 0
                    ):
                        category_uuid = router["wait"]["timeout"]["category_uuid"]
                    else:
                        return None  # We're stuck here forever --> exit here.
            else:
                for case in router["cases"]:
                    if case["type"] == "has_group":
                        group_name = case["arguments"][1]
                        if group_name in operand:
                            # Note: We ignore the Group UUID here.
                            category_uuid = case["category_uuid"]
                            break
                    elif case["type"] == "has_phrase":
                        if case["arguments"][0].lower() in operand.lower():
                            category_uuid = case["category_uuid"]
                            break
                    elif (
                        case["type"] == "has_only_text"
                        or case["type"] == "has_category"
                    ):
                        # These are case sensitive
                        if case["arguments"][0] == operand:
                            category_uuid = case["category_uuid"]
                            break
                    elif case["type"] == "has_any_word":
                        matched = False
                        for word in case["arguments"][0].split():
                            for input_word in operand.split():
                                if word.lower() == input_word.lower():
                                    matched = True
                        if matched:
                            category_uuid = case["category_uuid"]
                            break
                    elif case["type"] == "has_text":
                        if case["arguments"] != []:
                            raise ValueError(
                                "has_text case type must not have arguments"
                            )
                        if operand.strip() != "":
                            category_uuid = case["category_uuid"]
                            break
                    elif case["type"] == "has_email":
                        if case["arguments"] != []:
                            raise ValueError(
                                "has_email case type must not have arguments"
                            )
                        if len(re.findall(r"[\w]+@[\w]+\.[\w]+", operand)) > 0:
                            # This might differ from the RapidPro implementation.
                            category_uuid = case["category_uuid"]
                            break
                    elif case["type"] == "has_number_between":
                        # This might differ from the RapidPro implementation.
                        if len(case["arguments"]) != 2:
                            raise ValueError("has_number_between must have 2 arguments")
                        try:
                            number = float(operand)
                        except ValueError:
                            number = None
                        if number is not None and float(
                            case["arguments"][0]
                        ) <= number <= float(case["arguments"][1]):
                            category_uuid = case["category_uuid"]
                            break
                    elif case["type"] == "has_number_lt":
                        # This might differ from the RapidPro implementation.
                        try:
                            number = float(operand)
                        except ValueError:
                            number = None
                        if number is not None and number < float(case["arguments"][0]):
                            category_uuid = case["category_uuid"]
                            break
                    elif case["type"] == "has_number_gt":
                        # This might differ from the RapidPro implementation.
                        try:
                            number = float(operand)
                        except ValueError:
                            number = None
                        if number is not None and number > float(case["arguments"][0]):
                            category_uuid = case["category_uuid"]
                            break

            # Find the category matching the case and get its exit_uuid
            exit_uuid = None
            for category in router["categories"]:
                if category["uuid"] == category_uuid:
                    exit_uuid = category["exit_uuid"]
            if exit_uuid is None:
                raise ValueError(
                    "No valid exit_uuid in router of node with uuid "
                    + current_node["uuid"]
                )
        else:  # router["type"] == "random"
            # Get the exit_uuid from a random category
            random_choice = context.random_choices.pop(0)
            exit_uuid = router["categories"][random_choice]["exit_uuid"]

        # Find the exit we take here and get its destination_uuid
        destination_uuid = (
            -1
        )  # -1 because None is a valid value indicating the end of a flow
        for exit in current_node["exits"]:
            if exit["uuid"] == exit_uuid:
                destination_uuid = exit.get("destination_uuid", None)
                break
        if destination_uuid == -1:
            raise ValueError(
                "No valid destination_uuid in router of node with uuid "
                + current_node["uuid"]
            )
    return destination_uuid


# List of actions: https://app.rapidpro.io/mr/docs/flows.html#actions
action_value_fields = {
    "add_contact_groups": (lambda x: x["groups"][0]["name"]),
    "add_contact_urn": (lambda x: x["path"]),
    "add_input_labels": (lambda x: x["labels"][0]["name"]),
    "call_classifier": (lambda x: x["classified"]["name"]),
    "call_resthook": (lambda x: x["resthook"]),
    "call_webhook": (lambda x: x["url"]),
    "enter_flow": (lambda x: x["flow"]["name"]),
    "open_ticket": (lambda x: x["subject"]),
    "play_audio": (lambda x: x["audio_url"]),
    "remove_contact_groups": (
        lambda x: x["groups"][0]["name"] if x["groups"] else "ALL"
    ),
    "say_msg": (lambda x: x["text"]),
    "send_broadcast": (lambda x: x["text"]),
    "send_email": (lambda x: x["subject"]),
    "send_msg": (lambda x: x["text"]),
    "set_contact_channel": (lambda x: x["channel"]["name"]),
    "set_contact_field": (lambda x: x["field"]["key"]),
    "set_contact_language": (lambda x: x["language"]),
    "set_contact_name": (lambda x: x["name"]),
    "set_contact_status": (lambda x: x["status"]),
    "set_contact_timezone": (lambda x: x["timezone"]),
    "set_run_result": (lambda x: x["name"]),
    "start_session": (lambda x: x["flow"]["name"]),
    "transfer_airtime": (lambda x: "Amount"),
}


def process_actions(node, context):
    """May modify the context."""

    outputs = []
    for action in node["actions"]:
        # Log the action, regardless of its type
        # TODO: Try/catch in case of unrecognized action/missing field?
        action_type = action["type"]
        action_value = action_value_fields[action_type](action)
        outputs.append((action_type, action_value))

        # We only support a very small subset of actions.
        if action_type == "add_contact_groups":
            for group in action["groups"]:
                context.group_names.append(group["name"])
        elif action_type == "enter_flow":
            # TODO: recurse, append outputs
            # We need to have all flows for that.
            # action["flow"]["name"]
            # action["flow"]["uuid"]
            pass
    return outputs


def traverse_flow(flow, context):
    """
    Traverse a given flow, assuming the user's group memberships
    as specified in group_names, which determine which path through
    the flow is taken.

    Traversal ends once we reach an exit with destination_uuid None.

    If we encounter a destination_uuid leading to a node not contained
    in the flow, the flow is considered erroneous and an error is raised.

    Returns:
        A list of strings, which are the outputs of send_msg actions
        that are encounters while traversing through the flow.

    Only supports send_msg actions and group switches
    TODO: Abort after too many steps (there may be cycles).
    """

    outputs = []
    current_node = flow["nodes"][0]
    while current_node is not None:
        outputs += process_actions(current_node, context)

        destination_uuid = find_destination_uuid(current_node, context)
        if destination_uuid is None:  # we've reached the exit
            break
        current_node = find_node_by_uuid(flow, destination_uuid)
        if current_node is None:
            raise ValueError("Destination_uuid {} is invalid.".format(destination_uuid))
    return outputs


def find_final_destination(flow, node, context):
    """Starting at node in flow, traverse the flow until we reach a
    destination that is not contained inside the flow.
    TODO: Abort after too many steps (there may be cycles).

    Returns:
        uuid of the destination outside the flow
    """

    while node is not None:
        process_actions(node, context)
        destination_uuid = find_destination_uuid(node, context)
        node = find_node_by_uuid(flow, destination_uuid)
    return destination_uuid
