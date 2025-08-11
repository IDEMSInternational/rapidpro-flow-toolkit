import csv
import tablib

from tests import TESTS_ROOT


def get_dict_from_csv(csv_file_path):
    with open(TESTS_ROOT / csv_file_path) as csv_file:
        csv_reader = csv.DictReader(csv_file)
        return [row for row in csv_reader]


def get_table_from_file(file_path, file_format="csv"):
    # format: Import file format.
    #     Supported file formats as supported by tablib,
    #     see https://tablib.readthedocs.io/en/stable/formats.html
    # Returns:
    #     tablib.Dataset
    with open(TESTS_ROOT / file_path) as data_stream:
        return tablib.import_set(data_stream, format=file_format)


def csv_join(*args):
    return "\n".join(args) + "\n"
