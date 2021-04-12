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
from django.db.models import TextChoices
from defopt import Parameter, signature, _parse_docstring
from typing import Dict, Optional
from typing import Type
import pathlib

from . import utils

class Text(str):
    """Wrapper class to be able to handle str types"""
    pass


type2field_type = {int: forms.IntegerField, str: forms.CharField, bool: forms.BooleanField,
                   Optional[bool]: forms.NullBooleanField, Text: forms.CharField,
                   pathlib.Path: forms.CharField, dict: forms.JSONField}

type2widget = {Text: forms.Textarea()}

@dataclass
class _Function:
    func: callable
    name: str
    form_class: object
    doc: str

    @classmethod
    def from_function(cls, func, *, name, config=None):
        form_class = function_to_form(func, name=name, config=config)
        return cls(func=func, name=name, form_class=form_class,
                   doc=form_class.__doc__)


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
        field = param_to_field(parameter, config)
        fields[parameter.name] = field
        if parameter.default is not Parameter.empty:
            defaults[parameter.name] = parameter.default
        if isinstance(field, forms.TypedChoiceField):
            field._parameter_name = parameter.name
            field._func_name = name
            if parameter.default and parameter.default is not Parameter.empty:
                print(field.choices)
                for potential_default in [parameter.default.name, parameter.default.value]:
                    if any(potential_default == x[0] for x in field.choices):
                        defaults[parameter.name] = potential_default
                        break
                else:
                    raise ValueError(f"Cannot figure out how to assign default for {parameter.name}: {parameter.default}")
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


@dataclass
class Coercer:
    """Wrapper so that we handle implicit string conversion of enum types :("""
    enum_type: object
    by_attribute: bool = False

    def __call__(self, value):
        print(f"COERCE: {self} {value}")
        try:
            resp = self._call(value)
            print(f"COERCED TO: {self} {value} => {resp}")
            return resp
        except Exception as e:
            import traceback
            print(f"FAILED TO COERCE {repr(value)}({value})")
            traceback.print_exc()
            raise
    def _call(self, value):
        if value and isinstance(value, self.enum_type):
            print("ALREADY INSTANCE")
            return value
        if self.by_attribute:
            print("BY ATTRIBUTE")
            return getattr(self.enum_type, value)
        try:
            print("BY __call__")
            resp = self.enum_type(value)
            print(f"RESULT: {resp} ({repr(resp)})")
            return resp
        except ValueError as e:
            import traceback
            traceback.print_exc()
            try:
                print("BY int coerced __call__")
                return self.enum_type(int(value))
            except ValueError as f:
                # could not coerce to int :(
                pass
            if isinstance(value, str):
                # fallback to some kind of name thing if necesary
                try:
                    return getattr(self.enum_type, value)
                except AttributeError:
                    pass
            raise e from e
        assert False, "Should not get here"


def param_to_field(param: Parameter, config: dict = None) -> forms.Field:
    """Convert a specific arg to a django form field.

    See function_to_form for config definition."""
    config = config or {}
    all_types = {**type2field_type, **(config.get("types") or {})}
    widgets = {**type2widget, **(config.get("widgets") or {})}
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
        utils.EnumRegistry.register(kind)
        field_type = forms.TypedChoiceField
        kwargs.update(make_enum_kwargs(param=param, kind=kind))
    else:
        field_type = get_for_param_by_type(all_types, param=param, kind=kind)
    if not field_type:
        raise ValueError(f"Field {param.name}: Unknown field type: {param.annotation}")
    # do not overwrite kwargs if already specified
    kwargs =  {**extra_kwargs(field_type, param), **kwargs}
    if field_type == forms.BooleanField and param.default is None:
        field_type = forms.NullBooleanField

    widget = get_for_param_by_type(widgets, param=param, kind=kind)
    if widget:
        kwargs['widget'] = widget
    return field_type(**kwargs)


def make_enum_kwargs(kind, param):
    kwargs = {}
    if all(isinstance(member.value, int) for member in kind):
        kwargs["choices"] = TextChoices(f'{kind.__name__}Enum', {member.name: (member.name, member.name) for
            member in kind}).choices
        kwargs["coerce"] = Coercer(kind, by_attribute=True)
    else:
        # we set up all the kinds of entries to make it a bit easier to do the names and the
        # values...
        kwargs["choices"] = TextChoices(f'{kind.__name__}Enum', dict([(member.name, (str(member.value),
            member.name)) for member in kind] + [(str(member.value), (member.name, member.name)) for
                member in kind])).choices
        kwargs["coerce"] = Coercer(kind)
    # coerce back
    if isinstance(param.default, kind):
        kwargs["initial"] = param.default.value
    return kwargs


def get_for_param_by_type(dct, *, param, kind):
    """Grab the appropriate element out of dict based on param type.

    Ordering:
        1. param.name (i.e., something custom specified by user)
        2. param.annotation
        3. underlying type if typing.Optional
    """
    if elem := dct.get(param.name, dct.get(param.annotation, dct.get(kind))):
        return elem
    for k, v in dct.items():
        if inspect.isclass(k) and issubclass(kind, k) or k == kind:
            return v

def extra_kwargs(field_type, param):
    kwargs = {}
    if param.default is Parameter.empty:
        kwargs["required"] = True
    elif param.default is None:
        kwargs["required"] = False
        # need this so that empty values get passed through to function correctly!
        if 'empty_value' in inspect.signature(field_type).parameters:
            kwargs['empty_value'] = None
    else:
        kwargs["required"] = False
        kwargs.setdefault("initial", param.default)
    if param.doc:
        kwargs["help_text"] = param.doc
    return kwargs


