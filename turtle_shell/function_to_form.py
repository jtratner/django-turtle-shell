"""
Function to a Form
------------------

Converts function signatures into django forms.

NOTE: with enums it's recommended to use the string version, since the value will be used as the
representation to the user (and generally numbers aren't that valuable)
"""
import enum
import inspect
import re
import typing

from dataclasses import dataclass
from django import forms
from defopt import Parameter, signature, _parse_docstring
from typing import Dict, Optional
from typing import Type
import pathlib


type2field_type = {int: forms.IntegerField, str: forms.CharField, bool: forms.BooleanField,
                   Optional[bool]: forms.NullBooleanField,
                   pathlib.Path: forms.CharField, dict: forms.JSONField}

@dataclass
class _Function:
    func: callable
    name: str
    form_class: object

    @classmethod
    def from_function(cls, func, *, name):
        from turtle_shell.function_to_form import function_to_form
        return cls(func=func, name=name, form_class=function_to_form(func, name=name))


def doc_mapping(str) -> Dict[str, str]:
    return {}


def function_to_form(func, *, config: dict = None, name: str=None) -> Type[forms.Form]:
    """Convert a function to a Django Form.

    Args:
        func: the function to be changed
        config: A dictionary with keys ``widgets`` and ``fields`` each mapping types/specific
        arguments to custom fields
    """
    name = name or func.__qualname__
    sig = signature(func)
    # i.e., class body for form
    fields = {}
    defaults = {}
    for parameter in sig.parameters.values():
        fields[parameter.name] = param_to_field(parameter, config)
        if parameter.default is not Parameter.empty:
            defaults[parameter.name] = parameter.default
    fields["__doc__"] = re.sub("\n+", "\n", _parse_docstring(inspect.getdoc(func)).text)
    form_name = "".join(part.capitalize() for part in func.__name__.split("_"))


    class BaseForm(forms.Form):
        _func = func
        _input_defaults = defaults
        # use this for ignoring extra args from createview and such
        def __init__(self, *a, instance=None, user=None, **k):
            from crispy_forms.helper import FormHelper
            from crispy_forms.layout import Submit

            super().__init__(*a, **k)
            self.user = user
            self.helper = FormHelper(self)
            self.helper.add_input(Submit('submit', 'Execute!'))

        def execute_function(self):
            # TODO: reconvert back to enum type! :(
            return func(**self.cleaned_data)

        def save(self):
            from .models import ExecutionResult
            obj = ExecutionResult(func_name=name,
                                  input_json=self.cleaned_data,
                                  user=self.user)
            obj.save()
            return obj


    return type(form_name, (BaseForm,), fields)


def is_optional(annotation):
    if args := typing.get_args(annotation):
        return len(args) == 2 and args[-1] == type(None)


def get_type_from_annotation(param: Parameter):
    if is_optional(param.annotation):
        return typing.get_args(param.annotation)[0]
    if typing.get_origin(param.annotation):
        raise ValueError(f"Field {param.name}: type class {param.annotation} not supported")
    return param.annotation


def param_to_field(param: Parameter, config: dict = None) -> forms.Field:
    """Convert a specific arg to a django form field.

    See function_to_form for config definition."""
    config = config or {}
    all_types = dict(type2field_type)
    all_types.update(config.get("types", {}))
    widgets = config.get("widgets") or {}
    field_type = None
    kwargs = {}
    kind = get_type_from_annotation(param)
    is_enum_class = False
    try:
        is_enum_class = issubclass(kind, enum.Enum)
    except TypeError:
        # e.g. stupid generic type stuff
        pass
    if is_enum_class:
        field_type = forms.TypedChoiceField
        kwargs["coerce"] = kind
        kwargs["choices"] = [(member.name, member.value) for member in kind]
        # coerce back
        if isinstance(param.default, kind):
            kwargs["initial"] = param.default.value
    else:
        field_type = all_types.get(param.annotation, all_types.get(kind))
        for k, v in all_types.items():
            if field_type:
                break
            if inspect.isclass(k) and issubclass(kind, k) or k == kind:
                field_type = v
                break
        if not field_type:
            raise ValueError(f"Field {param.name}: Unknown field type: {param.annotation}")
    if param.default is Parameter.empty:
        kwargs["required"] = True
    elif param.default is None:
        kwargs["required"] = False
    else:
        kwargs["required"] = False
        kwargs.setdefault("initial", param.default)
    if param.doc:
        kwargs["help_text"] = param.doc
    for k, v in widgets.items():
        if isinstance(k, str):
            if param.name == k:
                kwargs["widget"] = v
                break
            continue
        if issubclass(k, param.annotation):
            kwargs["widget"] = v
            break
    return field_type(**kwargs)


