import enum
import json

import pytest
from django import forms

from .utils import compare_form_field
from turtle_shell.function_to_form import param_to_field
import turtle_shell
from defopt import Parameter
from typing import Optional
import typing


class Color(enum.Enum):
    red = enum.auto()
    green = enum.auto()
    yellow = enum.auto()


COLOR_CHOICES = [(e.value, e.value) for e in Color]


class Flag(enum.Enum):
    is_apple = "is_apple"
    is_banana = "is_banana"


FLAG_CHOICES = [(e.value, e.value) for e in Flag]


class Text(str):
    pass


def example_func(
    *,
    int_arg: int,
    int_arg_with_default: int = 5,
    bool_arg_default_true: bool = True,
    bool_arg_default_false: bool = False,
    bool_arg_no_default: bool,
    str_arg: str,
    str_arg_with_default: str = "whatever",
    text_arg: Text,
    text_arg_with_default: Text = Text("something"),
    enum_auto: Color,
    enum_auto_not_required: Color = None,
    enum_auto_with_default: Color = Color.green,
    enum_str: Flag,
    enum_str_with_default: Flag = Flag.is_apple,
    undocumented_arg: str = None,
):
    """
    First line of text content should be there.

    Args:
        int_arg: Browser native int field
        int_arg_with_default: Browser native int field with a default
        bool_arg_default_true: should be checked checkbox
        bool_arg_default_false: should be unchecked checkbox
        bool_arg_no_default: Bool arg with a dropdown
        str_arg: should be small field
        str_arg_with_default: should be small field with text in it
        text_arg: should have a big text field
        text_arg_with_default: should have big text field with something filled in
        enum_auto: should be choices with key names
        enum_auto_not_required: choice field not required
        enum_auto_with_default: choice field with entry selected
        enum_str: should be choices with string values

    Later lines of content here.

    """


class ExpectedFormForExampleFunc(forms.Form):
    """
    First line of text content should be there.

    Later lines of content here.
    """

    int_arg = forms.IntegerField()
    int_arg_with_default = forms.IntegerField(initial=5)
    bool_arg_default_true = forms.BooleanField(initial=True)
    bool_arg_default_false = forms.BooleanField(initial=False)
    bool_arg_no_default = forms.BooleanField()
    str_arg = forms.CharField()
    str_arg_with_default = forms.CharField(initial="whatever")
    # TODO: different widget
    text_arg = forms.CharField()
    # TODO: different widget
    text_arg_with_default = forms.CharField(initial="something")
    enum_auto = forms.ChoiceField


def _make_parameter(name, annotation, doc="", **kwargs):
    """helper for simple params :) """
    return Parameter(
        name=name,
        kind=Parameter.KEYWORD_ONLY,
        default=kwargs.get("default", Parameter.empty),
        annotation=annotation,
        doc=doc,
    )


@pytest.mark.parametrize(
    "arg,expected",
    [
        (_make_parameter("int", int, ""), forms.IntegerField(required=True)),
        (
            _make_parameter("int_none_default_not_required", int, default=None),
            forms.IntegerField(required=False),
        ),
        (
            _make_parameter("int_default", int, default=-1),
            forms.IntegerField(initial=-1, required=False),
        ),
        (
            _make_parameter("str_doc", str, "some doc"),
            forms.CharField(help_text="some doc", required=True),
        ),
        (
            _make_parameter("str_doc_not_required", str, "some doc", default="a"),
            forms.CharField(required=False, initial="a", help_text="some doc"),
        ),
        (
            _make_parameter("str_doc_falsey", str, "some doc", default=""),
            forms.CharField(initial="", required=False, help_text="some doc"),
        ),
        (
            _make_parameter("bool_falsey", bool, "some doc", default=False),
            forms.BooleanField(required=False, initial=False, help_text="some doc"),
        ),
        (
            _make_parameter("bool_truthy", bool, "some doc", default=True),
            forms.BooleanField(required=False, initial=True, help_text="some doc"),
        ),
        (
            _make_parameter("bool_required", bool, "some doc"),
            forms.BooleanField(required=True, help_text="some doc"),
        ),
        (
            _make_parameter("enum_auto", Color),
            forms.TypedChoiceField(coerce=Color, choices=COLOR_CHOICES),
        ),
        (
            _make_parameter("enum_auto_default", Color, "another doc", default=Color.green),
            forms.TypedChoiceField(
                coerce=Color,
                initial=Color.green.value,
                choices=COLOR_CHOICES,
                required=False,
                help_text="another doc",
            ),
        ),
        (
            _make_parameter("enum_str", Flag),
            forms.TypedChoiceField(coerce=Flag, choices=FLAG_CHOICES),
        ),
        (
            _make_parameter("enum_str_default", Flag, default=Flag.is_apple),
            forms.TypedChoiceField(
                coerce=Flag, initial="is_apple", choices=FLAG_CHOICES, required=False
            ),
        ),
        (
            _make_parameter("optional_bool", Optional[bool], default=True),
            forms.NullBooleanField(initial=True, required=False)
        ),
    ],
    ids=lambda x: x.name if hasattr(x, "name") else x,
)
def test_convert_arg(arg, expected):
    field = param_to_field(arg)
    compare_form_field(arg.name, field, expected)


def test_custom_widgets():
    param = _make_parameter("str_large_text_field", Text, "some doc", default="")
    text_input_widget = forms.TextInput(attrs={"size": "80", "autocomplete": "off"})
    compare_form_field(
        "str_large_text_field",
        param_to_field(
            param, {"widgets": {Text: text_input_widget}, "types": {Text: forms.CharField}},
        ),
        forms.CharField(
            widget=text_input_widget, help_text="some doc", initial="", required=False
        ),
    )


def test_validators():
    # something about fields failing validation
    pass


def execute_gql_and_get_input_json(func, gql):
    registry = turtle_shell.get_registry()
    registry.clear()
    registry.add(func)
    result = registry.schema.execute(gql)
    data = result.data
    assert not result.errors
    return json.loads(list(data.values())[0]["result"]["inputJson"])
    # data = json.loads(result["data"]["result"]["inputJson"])
    # return data

def test_defaults(db):
    # defaults should be passed through
    def myfunc(a: bool=True, b: str="whatever"):
        pass

    resp = execute_gql_and_get_input_json(myfunc, "mutation { executeMyfunc(input: {}) { result { inputJson }}}")
    assert resp == {"a": True, "b": "whatever"}

@pytest.mark.xfail
def test_default_none(db):

    # defaults should be passed through
    def myfunc(a: bool=None, b: str=None):
        pass

    resp = execute_gql_and_get_input_json(myfunc, "mutation { executeMyfunc(input: {}) { result { inputJson }}}")
    # sadly None's get replaced :(
    assert resp == {"a": None, "b": None}

def test_error_with_no_default(db):

    # no default should error
    def my_func(*, a: bool, b: str):
        pass
    registry = turtle_shell.get_registry()
    registry.clear()
    registry.add(my_func)
    gql = "mutation { executeMyfunc(input: {}) { result { inputJson }}}"
    result = registry.schema.execute(gql)
    assert result.errors


@pytest.mark.parametrize(
    "parameter,exception_type,msg_regex",
    [
        (_make_parameter("union_type", typing.Union[bool, str]), ValueError, "type class.*not supported"),
    ])
def test_exceptions(parameter, exception_type, msg_regex):
    with pytest.raises(exception_type, match=msg_regex):
        param_to_field(parameter)
