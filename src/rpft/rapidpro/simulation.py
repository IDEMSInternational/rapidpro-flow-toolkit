import re
import copy
import subprocess
import os
import tempfile
import json


GOPATH = os.environ.get("GOPATH") 
if GOPATH is None:
    GOPATH = "/home/runner/go" # for GH CI

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
    context_dict = json.dumps(context.__dict__)
    while current_node is not None:
        outputs += process_actions(current_node, context)

        destination_uuid = find_destination_uuid(current_node, context)
        if destination_uuid is None:  # we've reached the exit
            break
        current_node = find_node_by_uuid(flow, destination_uuid)
        if current_node is None:
            raise ValueError("Destination_uuid {} is invalid.".format(destination_uuid))
    context = Context(**json.loads(context_dict))
    return outputs


def traverse_flowrunner(flow, context, uuid=None, flow_name=None, expected_outputs=None,
                         testcls=None, test_name=None):
    if uuid is None and flow_name is None:
        fr = Flowrunner.from_flow(flow, context)
    else:
        if uuid is None:
            uuid = [f for f in flow["flows"] if f["name"] == flow_name][0]['uuid']
        fr = Flowrunner.from_dict(flow, uuid, context)

    # deal with random_choices
    fr_outputs = fr.get_messages(context.inputs)
    if context.random_choices != [] and expected_outputs is not None:
        for i in range(50):
            if fr_outputs == expected_outputs:
                continue
            fr_outputs = fr.get_messages(context.inputs)

    error_msg = f"Flowrunner not equal to traverse_flows"
    if context.random_choices != []:
        error_msg += "\nrandom_choice may be the issue"

    # Heavy debug: don't delete the files
    if fr_outputs != expected_outputs:
        error_msg += "\n" + " ".join(fr.command) + f"\ninputs: {context.inputs}"
        # disable file deletion
        fr.file_name = ""
        fr.contact = None

    if test_name is None:
        # get flow_name for more decriptive test naming
        tmp_flow = flow
        if "flows" in tmp_flow.keys():
            tmp_flow = tmp_flow["flows"]
        if type(tmp_flow) is not list:
            tmp_flow = [tmp_flow]
        if uuid is not None:
            flow_name = [f for f in tmp_flow if f["uuid"] == uuid][0]["name"]
        else:
            flow_name = tmp_flow[0]["name"]
        test_name = f"New Test Equivalence: {flow_name}"

    if testcls:
        with testcls.subTest(test_name):
            testcls.assertEqual(fr_outputs, expected_outputs, error_msg)

    return fr_outputs


class Flowrunner():
    prefix = 'temp_flow_'

    def __init__(self, file, uuid, contact=None):
        self.command = [os.path.join(GOPATH, "bin", "flowrunner")]
        if contact is not None:
            self.command.append("-contact")
            self.command.append(contact)
        self.command.append(file)
        self.command.append(uuid)

        self.file_name = file
        self.contact = contact
        self.lines = []

    def readlines(self, inputs=None):
        if inputs is not None:
            inputs = [(i+'\n' if i is not None else "/timeout\n") for i in inputs]
        if inputs is None:
            inputs = []

        self.lines = []
        with subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
        ) as process:
            while len(self.lines) < 1000:
                line = process.stdout.readline()

                if line == '':
                    break
                elif line.startswith("unable to read"):
                    raise Exception(f"Flow is malformed, likely has `uuid: null`: {line}\n{' '.join(self.command)}")
                elif line.startswith('⏳ waiting for message'):
                    try:
                        process.stdin.write(inputs.pop(0))
                    except IndexError:
                        process.stdin.write("\n")
                        print("Warning, tests should specify input when expecting wait_for_response, in future this will be treated as an error")
                    process.stdin.flush()
                    
                self.lines.append(line)
        return self.lines

    def get_messages(self, inputs=None):
        outputs = []
        for line in self.readlines(inputs):
            
            if line.startswith("💬 message created "):
                outputs.append(("send_msg", line[19:-2]))
            elif line.startswith("> 💬 message created "):
                outputs.append(("send_msg", line[21:-2]))
            elif line.startswith("✏️ field "):
                outputs.append((
                    "set_contact_field",
                     re.findall(r"✏️ field '(.*?)' changed to", line)[0]
                ))
            elif line.startswith("👪 added to "):
                outputs.append((
                    "add_contact_groups",
                     re.findall(r"👪 added to '(.*?)'", line)[0]
                ))
            elif line.startswith("👪 removed from "):
                outputs.append((
                    "remove_contact_groups",
                     re.findall(r"👪 removed from '(.*?)'", line)[0]
                ))
            elif line.startswith("📛 name changed to "):
                outputs.append((
                    "set_contact_name",
                     re.findall(r"📛 name changed to '(.*?)'", line)[0]
                ))
            elif line.startswith("📈 run result "):
                result = re.findall(r"📈 run result '(.*?)'", line)[0]
                if result != 'dummy':
                    print(line)
                else:
                    outputs.append((
                        "set_run_result",
                        re.findall(r"📈 run result '(.*?)'", line)[0]
                    ))
            elif line.startswith("↪️"):
                pass
            elif line.startswith(">"):
                pass
            elif line.startswith("⏳ waiting for message"):
                pass
            else:
                print(line)
        return outputs

    @classmethod
    def from_flow(cls, flow, context: Context):
        uuid = flow['uuid']

        new_dict = {
            "version": "13",
            "site": "https://rapidpro.idems.international",
            "flows": [flow],
        }
        return cls.from_dict(new_dict, uuid, context)

    @classmethod
    def from_dict(cls, render_output, uuid, context):
        """
        flowrunner requires json file as input, this creates a temp json file
        """
        new_dict = copy.deepcopy(render_output)
        tmp_file = tempfile.NamedTemporaryFile(
            mode='w+t', 
            delete=False,
            suffix='.json', 
            prefix=cls.prefix
        )

        # Patch issue with flowrunner needing fields to be set
        def find_fields(obj):
            """
            Recursively finds all fields referrenced in the flow.
            """
            if isinstance(obj, dict):
                if (list(obj.keys()) == ["key", "name"]) or (list(obj.keys()) == ["key", "name", "type"]):
                    yield obj
                else:
                    for value in obj.values():
                        yield from find_fields(value)
            elif isinstance(obj, list):
                for item in obj:
                    yield from find_fields(item)
        fields = list(find_fields(new_dict['flows']))
        if len(fields) != 0:
            print("Warning: in future fields should be populated during rendering")
            for f in fields:
                if "type" not in f.keys():
                    f["type"] = "string"
            new_dict["fields"] = fields

        def find_groups(obj):
            """
            Recursively finds all fields referrenced in the flow.
            """
            if isinstance(obj, dict):
                if "groups" in obj.keys():
                    if type(obj["groups"]) is list:
                        if len(obj["groups"]) > 0:
                            if set(["uuid", "name"]).issubset(obj["groups"][0].keys()):
                                yield from obj["groups"]
                else:
                    for value in obj.values():
                        yield from find_groups(value)
            elif isinstance(obj, list):
                for item in obj:
                    yield from find_groups(item)
        if len(list(find_groups(new_dict['flows']))) != 0:
            print("Warning: in future groups should be populated during rendering")
            unique_group_set = set(frozenset(d.items()) for d in find_groups(new_dict['flows']))
            groups = [dict(f) for f in unique_group_set]
            new_dict["groups"] = groups

        # If there's no variables or groups, use default contact
        if sum(len(context.__dict__[key]) for key in ["group_names", "variables"]) == 0:
            tmp_file.write(json.dumps(new_dict))
            tmp_file.flush()
            tmp_file.close()
            return cls(tmp_file.name, uuid)

        fields = {key[8:]: {"text": val} for key, val in context.variables.items() if key.startswith("@fields.")}

        if "fields" not in new_dict.keys():
            new_dict["fields"] = []
        new_dict['fields'] += [{"key": key, "name": key, "type": list(val.keys())[0]} for key, val in fields.items()]
        contact = {
            "uuid": "ba96bf7f-bc2a-4873-a7c7-254d1927c4e3",
            "id": 1234567,
            "name": "Ben Haggerty",
            "status": "active",
            "created_on": "2018-01-01T12:00:00.000000000-00:00",
            "fields": fields,
            "timezone": "America/Guayaquil",
            "urns": [
                "tel:+12065551212",
                "facebook:1122334455667788",
                "mailto:ben@macklemore"
            ],
            "groups": context.group_names,
        }
        contact_file = tempfile.NamedTemporaryFile(
            mode='w+t', 
            delete=False,
            suffix='.json', 
            prefix=cls.prefix
        )
        contact_file.write(json.dumps(contact))
        contact_file.flush()
        contact_file.close()
        tmp_file.write(json.dumps(new_dict))
        tmp_file.flush()
        tmp_file.close()
        return cls(tmp_file.name, uuid, contact_file.name)

    def __del__(self):
        """
        Destructor called when the instance is garbage collected.
        Ensures the temporary file is closed and deleted if it exists.
        """
        if self.prefix in self.file_name:
            os.unlink(self.file_name)
        if self.contact is not None:
            if self.prefix in self.contact:
                os.unlink(self.contact)



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
