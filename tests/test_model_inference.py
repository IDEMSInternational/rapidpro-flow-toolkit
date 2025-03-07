from typing import List
import unittest
from pydantic import create_model, BaseModel

from rpft.parsers.common.model_inference import (
    get_value_for_type,
    infer_default_value,
    infer_type,
    model_from_headers,
    parse_header_annotations,
    type_from_string,
)


class TestModelInference(unittest.TestCase):
    def test_type_from_string(self):
        self.assertEqual(type_from_string(""), str)
        self.assertEqual(type_from_string("str"), str)
        self.assertEqual(type_from_string("int"), int)
        self.assertEqual(type_from_string("list"), list)
        self.assertEqual(type_from_string("List"), List)
        self.assertEqual(type_from_string("List[str]"), List[str])
        self.assertEqual(type_from_string("List[int]"), List[int])
        self.assertEqual(type_from_string("List[List[int]]"), List[List[int]])

    def test_get_value_for_type(self):
        self.assertEqual(get_value_for_type(int), 0)
        self.assertEqual(get_value_for_type(str), "")
        self.assertEqual(get_value_for_type(bool), False)
        self.assertEqual(get_value_for_type(List[str]), [])
        self.assertEqual(get_value_for_type(list), [])

        self.assertEqual(get_value_for_type(int, "5"), 5)
        self.assertEqual(get_value_for_type(str, "abc"), "abc")
        self.assertEqual(get_value_for_type(bool, "True"), True)
        self.assertEqual(get_value_for_type(bool, "TRUE"), True)

    def test_infer_type(self):
        self.assertEqual(infer_type("field:int"), int)
        self.assertEqual(infer_type("field:list"), list)
        self.assertEqual(infer_type("field:List[int]"), List[int])
        self.assertEqual(infer_type("field : list"), list)
        self.assertEqual(infer_type("field:int=5"), int)
        self.assertEqual(infer_type("field:int = 5"), int)
        self.assertEqual(infer_type("field : int = 5"), int)
        self.assertEqual(infer_type("field=5"), str)

    def test_infer_default_value(self):
        self.assertEqual(infer_default_value(int, "field:int"), 0)
        self.assertEqual(infer_default_value(list, "field:list"), [])
        self.assertEqual(infer_default_value(List[int], "field:List[int]"), [])
        self.assertEqual(infer_default_value(list, "field : list"), [])
        self.assertEqual(infer_default_value(int, "field:int=5"), 5)
        self.assertEqual(infer_default_value(int, "field:int = 5"), 5)
        self.assertEqual(infer_default_value(int, "field : int = 5"), 5)
        self.assertEqual(infer_default_value(str, "field=5"), "5")
        self.assertEqual(infer_default_value(str, "field = 5"), "5")

    def test_parse_header_annotations(self):
        self.assertEqual(parse_header_annotations("field:int=5"), (int, 5))

    def compare_models(self, model1, model2, **kwargs):
        self.assertEqual(model1(**kwargs).model_dump(), model2(**kwargs).model_dump())

    def test_model_from_headers(self):
        self.compare_models(
            model_from_headers("mymodel", ["field1"]),
            create_model(
                "Mymodel",
                field1=(str, ""),
            ),
        )
        self.compare_models(
            model_from_headers("mymodel", ["field1:int=5"]),
            create_model(
                "Mymodel",
                field1=(int, 5),
            ),
        )
        self.compare_models(
            model_from_headers("mymodel", ["field1:list"]),
            create_model(
                "Mymodel",
                field1=(list, []),
            ),
        )
        self.compare_models(
            model_from_headers("mymodel", ["field1:list"]),
            create_model(
                "Mymodel",
                field1=(list, []),
            ),
            field1=[1, 2, 3, 4],
        )

        class MySubmodel(BaseModel):
            sub1: str = ""
            sub2: int = 5

        self.compare_models(
            model_from_headers("mymodel", ["field1.sub1", "field1.sub2:int=5"]),
            create_model(
                "Mymodel",
                field1=(MySubmodel, MySubmodel()),
            ),
        )
        self.compare_models(
            model_from_headers("mymodel", ["field1.1", "field1.2"]),
            create_model(
                "Mymodel",
                field1=(list, ["", ""]),
            ),
        )
        self.compare_models(
            model_from_headers("mymodel", ["field1.1:int", "field1.2:int=5"]),
            create_model(
                "Mymodel",
                field1=(list, [0, 5]),
            ),
        )
        self.compare_models(
            model_from_headers(
                "mymodel",
                [
                    "field1.1.1",
                    "field1.1.2=a",
                    "field1.2.1=b",
                    "field1.2.2=c",
                ],
            ),
            create_model(
                "Mymodel",
                field1=(List[List[str]], [["", "a"], ["b", "c"]]),
            ),
        )
        self.compare_models(
            model_from_headers(
                "mymodel",
                [
                    "field1.1.sub1",
                    "field1.1.sub2:int=5",
                    "field1.2.sub1",
                    "field1.2.sub2:int=5",
                ],
            ),
            create_model(
                "Mymodel",
                field1=(List[MySubmodel], [MySubmodel(), MySubmodel()]),
            ),
        )
