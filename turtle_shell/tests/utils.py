from typing import Type
import inspect

from django import forms


def compare_form_field(name, actual, expected):
    """Compare important variables of two form fields"""
    try:
        assert type(actual) == type(expected)
    except AssertionError as e:
        # bare assert causes pytest rewrite, so we just add a bit around it
        raise AssertionError(f"Field type mismatch ({name}): {e}") from e
    actual_vars = vars(actual)
    expected_vars = vars(expected)
    actual_vars.pop("widget", None)
    expected_vars.pop("widget", None)
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
    shared_keys = list(set(actual_fields.keys()) & set(expected_fields.keys()))
    extra_keys = list(set(actual_fields.keys()) - set(expected_fields.keys()))
    missing_keys = list(set(expected_fields.keys()) - set(actual_fields.keys()))
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
