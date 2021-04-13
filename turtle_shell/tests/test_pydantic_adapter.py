from pydantic import BaseModel
import enum
from typing import List
from turtle_shell import pydantic_adapter
from .utils import execute_gql, execute_gql_and_get_input_json
import pytest


class Status(enum.Enum):
    complete = "complete"
    bad = "bad"


class NestedStructure(BaseModel):
    status: Status
    thing: str


class StructuredOutput(BaseModel):
    value: str
    nested_things: List[NestedStructure]


def test_get_nested_models():
    lst = pydantic_adapter.get_pydantic_models_in_order(StructuredOutput)
    assert lst == [NestedStructure, StructuredOutput]
    lst = pydantic_adapter.get_pydantic_models_in_order(NestedStructure)
    assert lst == [NestedStructure]


def test_structured_output(db):
    def myfunc(a: str) -> StructuredOutput:
        return StructuredOutput(
            value=a,
            nested_things=[
                NestedStructure(status=Status.bad, thing="other"),
                NestedStructure(status=Status.complete, thing="other2"),
            ],
        )

    result = execute_gql(
        myfunc,
        'mutation { executeMyfunc(input:{a: "whatever"}) { structuredOutput { nested_things { status }}}}',
    )
    assert not result.errors
    nested = result.data["executeMyfunc"]["output"]["nested_things"]
    assert list(sorted(nested)) == list(sorted([{"status": "bad"}, {"status": "complete"}]))


@pytest.mark.xfail
def test_duplicate_enum_reference(db):
    class StructuredDuplicatingStatus(BaseModel):
        # this extra status causes graphene reducer to complain cuz we don't cache the Enum model
        # :(
        status: Status
        nested_things: List[NestedStructure]

    def myfunc(a: str) -> StructuredDuplicatingStatus:
        return StructuredDuplicatingStatus(
            status=Status.complete,
            value=a,
            nested_things=[
                NestedStructure(status=Status.bad, thing="other"),
                NestedStructure(status=Status.complete, thing="other2"),
            ],
        )

    result = execute_gql(
        myfunc,
        'mutation { executeMyfunc(input:{a: "whatever"}) { structuredDuplicatingStatus { nested_things { status }}}}',
    )
    assert not result.errors
    nested = result.data["executeMyfunc"]["output"]["nested_things"]
    assert list(sorted(nested)) == list(sorted([{"status": "bad"}, {"status": "complete"}]))


@pytest.mark.xfail
def test_structured_input(db):
    class NestedInput(BaseModel):
        text: str

    class StructuredInput(BaseModel):
        a: str
        b: List[int]
        nested: List[NestedInput]

    inpt1 = StructuredInput(a="a", b=[1, 2, 3], nested=[NestedInput(text="whatever")])

    def myfunc(s: StructuredInput = inpt1) -> str:
        return "apples"

    inpt = execute_gql_and_get_input_json(
        myfunc, "mutation { executeMyfunc(input: {}) { result { inputJson}}}"
    )
    actual = StructuredInput.parse_obj(inpt["s"])
    assert actual == inpt1
