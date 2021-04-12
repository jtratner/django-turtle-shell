from typing import Type
import inspect
import turtle_shell

from django import forms
import json


def compare_form_field(name, actual, expected):
    """Compare important variables of two form fields"""
    try:
        assert type(actual) == type(expected)
    except AssertionError as e:
        # bare assert causes pytest rewrite, so we just add a bit around it
        raise AssertionError(f"Field type mismatch ({name}): {e}") from e
    actual_vars = vars(actual)
    expected_vars = vars(expected)
    for k in ("widget", "_func_name", "_parameter_name"):
        actual_vars.pop(k, None)
        expected_vars.pop(k, None)
    try:
        assert actual_vars == expected_vars
    except AssertionError as e:
        # bare assert causes pytest rewrite, so we just add a bit around it
        raise AssertionError(f"Field mismatch ({name}): {e}") from e


def compare_forms(actual: Type[forms.Form], expected: Type[forms.Form]):
    """Compare two forms.

    Checks:
        1. Shared fields are the same (see compare_form_field)
        2. Both forms have the same set of fields
        3. Both forms have the same docstring
    """
    actual_fields = actual.declared_fields
    expected_fields = expected.declared_fields
    excluded_keys = {'_func_name', '_parameter_name'}
    shared_keys = list(set(actual_fields.keys()) & set(expected_fields.keys()) - excluded_keys)
    extra_keys = list(set(actual_fields.keys()) - set(expected_fields.keys()) - excluded_keys)
    missing_keys = list(set(expected_fields.keys()) - set(actual_fields.keys()) - excluded_keys)
    for name in shared_keys:
        actual_field = actual_fields[name]
        expected_field = expected_fields[name]
        compare_form_field(name, actual_field, expected_field)
    assert not extra_keys, f"Found unexpected form fields:\n{extra_keys}"
    assert not missing_keys, f"Expected fields missing:\n{missing_keys}"
    try:
        assert actual_fields.keys() == expected_fields.keys()
    except AssertionError as e:
        # bare assert causes pytest rewrite, so we just add a bit around it
        raise AssertionError(f"Forms have different field names: {e}") from e
    try:
        assert inspect.getdoc(actual) == inspect.getdoc(expected)
    except AssertionError as e:
        print(repr(inspect.getdoc(actual)))
        print(repr(inspect.getdoc(expected)))
        # bare assert causes pytest rewrite, so we just add a bit around it
        raise AssertionError(f"Forms have different docstrings: {e}") from e


def execute_gql(func, gql):
    registry = turtle_shell.get_registry()
    registry.clear()
    registry.add(func)
    result = registry.schema.execute(gql)
    return result

def execute_gql_and_get_input_json(func, gql):
    """Helper to make it easy to test default setting"""
    result = execute_gql(func, gql)
    data = result.data
    assert not result.errors
    result_from_response = list(data.values())[0]["result"]
    assert result_from_response
    return json.loads(result_from_response["inputJson"])
    # data = json.loads(result["data"]["result"]["inputJson"])
    # return data
