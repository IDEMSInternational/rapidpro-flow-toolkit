import logging
import string

from rapidpro.models.common import Exit
from rapidpro.utils import generate_new_uuid

logger = logging.getLogger(__name__)


class BaseRouter:
    def __init__(self, result_name=None):
        self.type = None
        self.categories = []
        self.result_name = result_name

    def set_result_name(self, result_name):
        # TODO: Check that this works
        self.result_name = result_name

    def _get_category_or_none(self, category_name):
        result = [c for c in self.get_categories() if c.name == category_name]
        if result:
            return result[0]

    def _add_category(self, category_name, destination_uuid):
        category = RouterCategory(category_name, destination_uuid)
        self.categories.append(category)
        return self.categories[-1]

    def get_or_create_category(self, category_name, destination_uuid):
        category = self._get_category_or_none(category_name)
        return category if category else self._add_category(category_name, destination_uuid)

    def get_exits(self):
        return [c.get_exit() for c in self.get_categories()]

    def get_categories(self):
        # TODO: Remove this and have the default category included in the list for the SwitchRouter
        raise NotImplementedError

    def render(self):
        raise NotImplementedError


class SwitchRouter(BaseRouter):

    def __init__(self, operand, result_name=None, wait_for_message=False):
        super().__init__(result_name)
        self.type = 'switch'
        self.operand = operand
        self.cases = []
        self.wait_for_message = wait_for_message
        # Add an implicit default category
        category = RouterCategory('Other', None)
        self.default_category = category
        # Indicates that a default category has been added by the user
        self.has_explicit_default_category = False

    def _get_case_or_none(self, comparison_type, arguments, category_uuid):
        for case in self.cases:
            if case.type == comparison_type \
                    and case.arguments == arguments \
                    and case.category_uuid == category_uuid:
                return case

    def _add_case(self, comparison_type, arguments, category_uuid):
        case = RouterCase(comparison_type, arguments, category_uuid)
        self.cases.append(case)
        return self.cases[-1]

    def get_or_create_case(self, comparison_type, arguments, category_name):
        category = self._get_category_or_none(category_name)
        if not category:
            raise ValueError(f'Category ({category_name}) not found. Please add category before adding the case')

        case = self._get_case_or_none(comparison_type, arguments, category.uuid)
        return case if case else self._add_case(comparison_type, arguments, category.uuid)

    def generate_category_name(self, comparison_arguments):
        # Auto-generate a category name that is guaranteed to be unique
        # TODO: Write tests for this
        category_name = '_'.join([str(a).title() for a in comparison_arguments])
        while self._get_category_or_none(category_name):
            category_name += "_alt"
        return category_name

    def add_choice(self, comparison_variable, comparison_type, comparison_arguments, category_name,
                   destination_uuid, is_default=False):
        if not category_name:
            category_name = self.generate_category_name(comparison_arguments)
        if is_default:
            self.update_default_category(destination_uuid, category_name)
            category = self.default_category
        else:
            category = self.get_or_create_category(category_name, destination_uuid)

        self.get_or_create_case(comparison_type, comparison_arguments, category.name)
        self.set_operand(comparison_variable)
        return category

    def update_default_category(self, destination_uuid, category_name=None):
        if self.has_explicit_default_category:
            logger.warning(f'Overwriting default category for Router')
        self.default_category.update_destination_uuid(destination_uuid)
        if category_name:
            self.default_category.update_name(category_name)
        if destination_uuid or category_name:
            self.has_explicit_default_category = True

    def get_categories(self):
        return self.categories + [self.default_category]

    def set_operand(self, operand):
        if not operand:
            return
        if self.operand and operand and self.operand != operand:
            logger.warning(f'Overwriting operand from {self.operand} -> {operand}')

        self.operand = operand

    def record_global_uuids(self, uuid_dict):
        for case in self.cases:
            if case.type == 'has_group':
                uuid_dict.record_group_uuid(case.arguments[1], case.arguments[0])

    def assign_global_uuids(self, uuid_dict):
        for case in self.cases:
            if case.type == 'has_group':
                case.arguments[0] = uuid_dict.get_group_uuid(case.arguments[1])

    def validate(self):
        # TODO: Add validation
        pass

    def render(self):
        self.validate()
        render_dict = {
            "type": self.type,
            "operand": self.operand,
            "cases": [case.render() for case in self.cases],
            "categories": [category.render() for category in self.get_categories()],
            "default_category_uuid": self.default_category.uuid
        }
        if self.wait_for_message:
            render_dict.update({
                "wait": {
                    "type": "msg",
                }
            })
        if self.result_name:
            render_dict.update({
                "result_name": self.result_name
            })
        return render_dict


class RandomRouter(BaseRouter):
    def __init__(self, result_name=None):
        super().__init__(result_name)
        self.type = 'random'

    def add_choice(self, category_name=None, destination_uuid=None):
        if not category_name:
            category = f'Bucket {len(self.categories) + 2}'
        self.get_or_create_category(category_name, destination_uuid)

    def get_categories(self):
        return self.categories

    def validate(self):
        # TODO: Add validation
        pass

    def render(self):
        render_dict = {
            "type": self.type,
            "categories": [category.render() for category in self.categories]
        }
        if self.result_name:
            render_dict.update({
                "result_name": self.result_name
            })
        return render_dict


class RouterCategory:
    def __init__(self, name, destination_uuid):
        """
        :param name: Name of the category
        :param destination_uuid: The UUID of the node that this category should point to
        """
        self.uuid = generate_new_uuid()
        self.name = name
        self.exit_uuid = generate_new_uuid()
        self.destination_uuid = destination_uuid

    def get_exit(self):
        return Exit(uuid=self.exit_uuid, destination_uuid=self.destination_uuid)

    def update_destination_uuid(self, uuid):
        self.destination_uuid = uuid

    def update_name(self, name):
        self.name = name 

    def render(self):
        return {
            'uuid': self.uuid,
            'name': self.name,
            'exit_uuid': self.exit_uuid,
        }


class RouterCase:
    def __init__(self, comparison_type, arguments, category_uuid):
        self.uuid = generate_new_uuid()
        self.type = comparison_type
        self.arguments = arguments
        self.category_uuid = category_uuid

    def render(self):
        return {
            'uuid': self.uuid,
            'type': self.type,
            'category_uuid': self.category_uuid,
            'arguments': self.arguments,
        }
