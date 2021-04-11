from typing import Type
import inspect

from django import forms


def compare_form_field(name, actual, expected):
    """Compare important variables of two form fields"""
    assert type(actual) == type(expected), f"Field type mismatch ({name})"
    actual_vars = vars(actual)
    expected_vars = vars(expected)
    actual_vars.pop("widget", None)
    expected_vars.pop("widget", None)
    assert actual_vars == expected_vars, f"Field mismatch ({name})"


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
    for name in shared_keys:
        actual_field = actual_fields[name]
        expected_field = expected_fields[name]
        compare_form_field(name, actual_field, expected_field)
    assert actual_fields.keys() == expected_fields.keys(), "Forms have different field names"
    assert inspect.getdoc(actual) == inspect.getdoc(expected), "Forms have different docstrings"
