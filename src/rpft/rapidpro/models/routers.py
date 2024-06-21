import logging

from rpft.rapidpro.models.common import Exit
from rpft.rapidpro.utils import generate_new_uuid
from rpft.parsers.creation.flowrowmodel import Condition, Edge

logger = logging.getLogger(__name__)


class BaseRouter:
    def __init__(self, result_name=None, categories=None):
        self.type = None
        self.categories = categories or []
        self.result_name = result_name

    def from_dict(data, exits):
        if data["type"] == "random":
            return RandomRouter.from_dict(data, exits)
        elif data["type"] == "switch":
            return SwitchRouter.from_dict(data, exits)
        else:
            raise ValueError("Router data has invalid router type.")

    def _get_result_name_and_categories_from_data(data, exits):
        categories = [
            RouterCategory.from_dict(category_data, exits)
            for category_data in data["categories"]
        ]
        result_name = None
        if "result_name" in data:
            result_name = data["result_name"]
        return result_name, categories

    def set_result_name(self, result_name):
        # TODO: Check that this works
        self.result_name = result_name

    def _get_category_or_none(self, category_name):
        result = [c for c in self.get_categories() if c.name == category_name]
        if result:
            return result[0]

    def get_category_by_uuid(self, uuid):
        # It might be better if cases had a reference to
        # a category, rather than their uuid.
        result = [c for c in self.get_categories() if c.uuid == uuid]
        if result:
            return result[0]
        else:
            raise KeyError("No Category with given uuid")

    def _add_category(self, category_name, destination_uuid):
        category = RouterCategory(category_name, destination_uuid)
        self.categories.append(category)
        return self.categories[-1]

    def get_or_create_category(self, category_name, destination_uuid):
        # If the category exists, this updates its destination uuid
        category = self._get_category_or_none(category_name)
        if category:
            category.update_destination_uuid(destination_uuid)
            return category
        else:
            return self._add_category(category_name, destination_uuid)

    def get_exits(self):
        return [c.get_exit() for c in self.get_categories()]

    def record_global_uuids(self, uuid_dict):
        pass

    def assign_global_uuids(self, uuid_dict):
        pass

    def get_categories(self):
        # TODO: Remove this and have the default category included in the list for the
        # SwitchRouter
        raise NotImplementedError

    def render(self):
        raise NotImplementedError

    def get_exit_edge_pairs(self, row_id):
        raise NotImplementedError


class SwitchRouter(BaseRouter):
    def __init__(
        self,
        operand,
        result_name=None,
        wait_timeout=None,
        cases=None,
        categories=None,
        default_category=None,
        no_response_category=None,
    ):
        """
        wait_timeout:
            None: There is no waiting for a user's message in this router
            0: Waiting for user's message, without a timeout
            >0: Waiting for user's message, with a timeout (in which case
                no_response_category is taken)
        """

        super().__init__(result_name)
        self.type = "switch"
        self.operand = operand
        self.cases = cases or []
        self.wait_timeout = wait_timeout

        self.has_explicit_default_category = False

        if default_category:
            self.default_category = default_category
            # Indicates that a default category has been added by the user
            self.has_explicit_default_category = True
        else:
            # Add an implicit default category
            category = RouterCategory("Other", None)
            self.default_category = category
        self.categories = categories or []

        self.has_explicit_no_response_category = False
        if self.wait_timeout:
            if no_response_category:
                self.no_response_category = no_response_category
                # Indicates that a No Response category has been added by the user
                self.has_explicit_no_response_category = True
            else:
                category = RouterCategory("No Response", None)
                self.no_response_category = category
        else:
            self.no_response_category = None
            if no_response_category:
                logger.warning(
                    "Router has No Response category but no wait timeout."
                    " Ignoring No Response category."
                )

    def from_dict(data, exits):
        result_name, categories = BaseRouter._get_result_name_and_categories_from_data(
            data, exits
        )
        cases = [RouterCase.from_dict(case_data) for case_data in data["cases"]]
        default_categories = [
            category
            for category in categories
            if category.uuid == data["default_category_uuid"]
        ]
        if not default_categories:
            raise ValueError("Default category uuid does not match any category.")
        no_response_category = None
        no_response_category_id = None
        wait_timeout = None
        if "wait" in data:
            wait_timeout = 0
            if "timeout" in data["wait"]:
                no_response_category_id = data["wait"]["timeout"]["category_uuid"]
                wait_timeout = int(data["wait"]["timeout"]["seconds"])
                no_response_categories = [
                    category
                    for category in categories
                    if category.uuid == no_response_category_id
                ]
                if not no_response_categories:
                    raise ValueError(
                        "No Response category uuid does not match any category."
                    )
                no_response_category = no_response_categories[0]
        other_categories = [
            category
            for category in categories
            if category.uuid
            not in [data["default_category_uuid"], no_response_category_id]
        ]
        return SwitchRouter(
            data["operand"],
            result_name,
            wait_timeout,
            cases,
            other_categories,
            default_categories[0],
            no_response_category,
        )

    def _get_case_or_none(self, comparison_type, arguments):
        for case in self.cases:
            if case.type == comparison_type and case.arguments == arguments:
                return case

    def _add_case(self, comparison_type, arguments, category_uuid):
        case = RouterCase(comparison_type, arguments, category_uuid)
        self.cases.append(case)
        return self.cases[-1]

    def create_case(self, comparison_type, arguments, category):
        return self._add_case(comparison_type, arguments, category.uuid)

    def generate_category_name(self, comparison_arguments):
        # Auto-generate a category name that is guaranteed to be unique
        # TODO: Write tests for this
        category_name = "_".join([str(a).title() for a in comparison_arguments])
        while self._get_category_or_none(category_name):
            category_name += "_alt"
        return category_name

    def add_choice(
        self,
        comparison_variable,
        comparison_type,
        comparison_arguments,
        category_name,
        destination_uuid,
        is_default=False,
    ):
        self.set_operand(comparison_variable)
        case = self._get_case_or_none(comparison_type, comparison_arguments)
        if case:
            # Case already exists. Only update the destination
            # category_name is ignored.
            category = self.get_category_by_uuid(case.category_uuid)
            category.update_destination_uuid(destination_uuid)
            return

        if not category_name:
            category_name = self.generate_category_name(comparison_arguments)
        if is_default:
            self.update_default_category(destination_uuid, category_name)
            category = self.default_category
        else:
            category = self.get_or_create_category(category_name, destination_uuid)
        self._add_case(comparison_type, comparison_arguments, category.uuid)
        return category

    def update_default_category(self, destination_uuid, category_name=None):
        if self.has_explicit_default_category:
            logger.warning("Overwriting default category for Router")
        self.default_category.update_destination_uuid(destination_uuid)
        if category_name:
            self.default_category.update_name(category_name)
        if destination_uuid or category_name:
            self.has_explicit_default_category = True

    def update_no_response_category(self, destination_uuid, category_name=None):
        if not self.wait_timeout:
            logger.warning(
                "Updating No Response category, but router has no wait timeout."
            )
        if self.has_explicit_no_response_category:
            logger.warning("Overwriting No Response category for Router")
        self.no_response_category.update_destination_uuid(destination_uuid)
        if category_name:
            self.no_response_category.update_name(category_name)
        if destination_uuid or category_name:
            self.has_explicit_no_response_category = True

    def has_wait(self):
        return self.wait_timeout is not None

    def has_positive_wait(self):
        return bool(self.wait_timeout)

    def get_categories(self):
        if self.no_response_category:
            return (
                self.categories + [self.default_category] + [self.no_response_category]
            )
        else:
            return self.categories + [self.default_category]

    def set_operand(self, operand):
        if not operand:
            return
        if self.operand and operand and self.operand != operand:
            logger.warning(f"Overwriting operand from {self.operand} -> {operand}")

        self.operand = operand

    def record_global_uuids(self, uuid_dict):
        for case in self.cases:
            if case.type == "has_group":
                uuid_dict.record_group_uuid(case.arguments[1], case.arguments[0])

    def assign_global_uuids(self, uuid_dict):
        for case in self.cases:
            if case.type == "has_group":
                case.arguments[0] = uuid_dict.get_group_uuid(case.arguments[1])

    def validate(self):
        # TODO: Add more validation
        if self.wait_timeout is not None:
            assert type(self.wait_timeout) is int
            assert self.wait_timeout >= 0
            if self.wait_timeout > 0:
                assert self.no_response_category is not None

    def render(self):
        self.validate()
        render_dict = {
            "type": self.type,
            "operand": self.operand,
            "cases": [case.render() for case in self.cases],
            "categories": [category.render() for category in self.get_categories()],
            "default_category_uuid": self.default_category.uuid,
        }
        if self.has_positive_wait():
            render_dict.update(
                {
                    "wait": {
                        "type": "msg",
                        "timeout": {
                            "seconds": self.wait_timeout,
                            "category_uuid": self.no_response_category.uuid,
                        },
                    }
                }
            )
        elif self.has_wait():
            render_dict.update(
                {
                    "wait": {
                        "type": "msg",
                    }
                }
            )
        if self.result_name is not None:
            render_dict.update({"result_name": self.result_name})
        return render_dict

    def get_exit_edge_pairs(self, row_id):
        pairs = []
        covered_category_uuids = set()
        for category in self.get_categories():
            for case in self.cases:
                # Find the case matching the category.
                if case.category_uuid == category.uuid:
                    covered_category_uuids.add(category.uuid)
                    arg_idx = 1 if self.operand == "@contact.groups" else 0
                    if self.operand in ["@contact.groups", "@child.run.status"]:
                        # For groups and expired/complete, var/type/name are implicit
                        condition = Condition(value=case.arguments[arg_idx])
                    else:
                        value = ""
                        if case.type not in RouterCase.NO_ARGS_TESTS:
                            value = case.arguments[arg_idx]
                        condition = Condition(
                            value=value,
                            variable=self.operand,
                            type=case.type,
                            name=category.name,
                        )
                    pairs.append(
                        (category.exit, Edge(from_=row_id, condition=condition))
                    )
                    break
        if self.default_category.uuid not in covered_category_uuids:
            # Sometimes, the default category is already covered by a specific case.
            # In that case, its edge has already been covered.
            pairs.append(
                (self.default_category.exit, Edge(from_=row_id))
            )  # By convention, the condition is blank rather than 'Other'
        if self.no_response_category:
            pairs.append(
                (
                    self.no_response_category.exit,
                    Edge(from_=row_id, condition=Condition(value=category.name)),
                )
            )
        return pairs


class RandomRouter(BaseRouter):
    def __init__(self, result_name=None, categories=None):
        super().__init__(result_name, categories)
        self.type = "random"

    def from_dict(data, exits):
        result_name, categories = BaseRouter._get_result_name_and_categories_from_data(
            data, exits
        )
        return RandomRouter(result_name, categories)

    def add_choice(self, category_name=None, destination_uuid=None):
        self.get_or_create_category(
            category_name if category_name else f"Bucket {len(self.categories) + 2}",
            destination_uuid,
        )

    def get_categories(self):
        return self.categories

    def validate(self):
        # TODO: Add validation
        pass

    def render(self):
        render_dict = {
            "type": self.type,
            "categories": [category.render() for category in self.categories],
        }
        if self.result_name:
            render_dict.update({"result_name": self.result_name})
        return render_dict

    def get_exit_edge_pairs(self, row_id):
        pairs = []
        for category in self.categories:
            pairs.append(
                (
                    category.exit,
                    Edge(from_=row_id, condition=Condition(value=category.name)),
                )
            )
        return pairs


class RouterCategory:
    def __init__(
        self, name, destination_uuid=None, uuid=None, exit_uuid=None, exit=None
    ):
        """
        :param name: Name of the category
        :param destination_uuid: The UUID of the node that this category should point to

        The destination of the category can be provided either as a destination_uuid or
        an exit.
        """
        self.uuid = uuid or generate_new_uuid()
        self.name = name
        if exit:
            self.exit = exit
        else:
            self.exit = Exit(
                uuid=exit_uuid or generate_new_uuid(), destination_uuid=destination_uuid
            )

    def from_dict(data, exits):
        """
        :param data: The router in json format, as in RapidPro flows
        :param exits: A list of exit objects containing an exit the category connects to
        """
        matching_exits = [exit for exit in exits if exit.uuid == data["exit_uuid"]]
        if not matching_exits:
            raise ValueError("RouterCategory with no matching exit.")
        return RouterCategory(
            name=data["name"], uuid=data["uuid"], exit=matching_exits[0]
        )

    def get_exit(self):
        return self.exit

    def update_destination_uuid(self, uuid):
        self.exit.destination_uuid = uuid

    def update_name(self, name):
        self.name = name

    def render(self):
        return {
            "uuid": self.uuid,
            "name": self.name,
            "exit_uuid": self.exit.uuid,
        }


class RouterCase:
    NO_ARGS_TESTS = {
        "has_date",
        "has_email",
        "has_error",
        "has_number",
        "has_state",
        "has_text",
        "has_time",
    }

    TEST_VALIDATIONS = {
        "all_words": lambda x: len(x) == 1,
        "has_any_word": lambda x: len(x) == 1,
        "has_beginning": lambda x: len(x) == 1,
        "has_category": lambda x: len(x) >= 1,
        "has_date": lambda x: len(x) == 0,
        "has_date_eq": lambda x: len(x) == 1,
        "has_date_gt": lambda x: len(x) == 1,
        "has_date_lt": lambda x: len(x) == 1,
        "has_district": lambda x: len(x) == 1,
        "has_email": lambda x: len(x) == 0,
        "has_error": lambda x: len(x) == 0,
        "has_group": lambda x: len(x) in {1, 2},  # uuid obligatory, name optional?
        "has_intent": lambda x: len(x) == 2,
        "has_number": lambda x: len(x) == 0,
        "has_number_between": lambda x: len(x) == 2,
        "has_number_eq": lambda x: len(x) == 1,
        "has_number_gt": lambda x: len(x) == 1,
        "has_number_gte": lambda x: len(x) == 1,
        "has_number_lt": lambda x: len(x) == 1,
        "has_number_lte": lambda x: len(x) == 1,
        "has_only_phrase": lambda x: len(x) == 1,
        "has_only_text": lambda x: len(x) == 1,
        "has_pattern": lambda x: len(x) == 1,
        "has_phone": lambda x: len(x) in {0, 1},
        "has_phrase": lambda x: len(x) == 1,
        "has_state": lambda x: len(x) == 0,
        "has_text": lambda x: len(x) == 0,
        "has_time": lambda x: len(x) == 0,
        "has_top_intent": lambda x: len(x) == 2,
        "has_ward": lambda x: len(x) == 2,
    }

    def __init__(self, comparison_type, arguments, category_uuid, uuid=None):
        self.uuid = uuid or generate_new_uuid()
        self.type = comparison_type
        self.category_uuid = category_uuid
        if self.type in RouterCase.NO_ARGS_TESTS:
            self.arguments = []
        else:
            self.arguments = arguments
        self.validate()

    def from_dict(data):
        return RouterCase(
            data["type"], data["arguments"], data["category_uuid"], data["uuid"]
        )

    def validate(self):
        if self.type not in RouterCase.TEST_VALIDATIONS:
            raise ValueError(f'Invalid router test type: "{self.type}"')
        if not RouterCase.TEST_VALIDATIONS[self.type](self.arguments):
            print(
                f"Warning: Invalid number of arguments {len(self.arguments)} for router"
                f'test type "{self.type}"'
            )

    def render(self):
        self.validate()
        return {
            "uuid": self.uuid,
            "type": self.type,
            "category_uuid": self.category_uuid,
            "arguments": self.arguments,
        }
