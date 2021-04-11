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

from django import forms
from defopt import Parameter, signature, _parse_docstring
from typing import Dict
from typing import Type


type2field_type = {int: forms.IntegerField, str: forms.CharField, bool: forms.BooleanField}


def doc_mapping(str) -> Dict[str, str]:
    return {}


def function_to_form(func, config: dict = None) -> Type[forms.Form]:
    """Convert a function to a Django Form.

    Args:
        func: the function to be changed
        config: A dictionary with keys ``widgets`` and ``fields`` each mapping types/specific
        arguments to custom fields
    """
    sig = signature(func)
    # i.e., class body for form
    fields = {}
    for parameter in sig.parameters.values():
        fields[parameter.name] = param_to_field(parameter, config)
    fields["__doc__"] = re.sub("\n+", "\n", _parse_docstring(inspect.getdoc(func)).text)
    fields["_func"] = func
    form_name = "".join(part.capitalize() for part in func.__name__.split("_"))

    def execute_function(self):
        # TODO: reconvert back to enum type! :(
        return func(**self.cleaned_data)

    fields["execute_function"] = execute_function

    return type(form_name, (forms.Form,), fields)


def param_to_field(param: Parameter, config: dict = None) -> forms.Field:
    """Convert a specific arg to a django form field.

    See function_to_form for config definition."""
    config = config or {}
    all_types = dict(type2field_type)
    all_types.update(config.get("types", {}))
    widgets = config.get("widgets") or {}
    field_type = None
    kwargs = {}
    if issubclass(param.annotation, enum.Enum):
        field_type = forms.TypedChoiceField
        kwargs["coerce"] = param.annotation
        kwargs["choices"] = [(member.value, member.value) for member in param.annotation]
        # coerce back
        if isinstance(param.default, param.annotation):
            kwargs["initial"] = param.default.value
    else:
        for k, v in all_types.items():
            if isinstance(k, str):
                if param.name == k:
                    field_type = v
                    break
                continue
            if issubclass(k, param.annotation):
                field_type = v
                break
        else:
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


def to_graphene_form_mutation(func):
    import graphene
    from graphene_django.forms.mutation import DjangoFormMutation

    form_klass = function_to_form(func)

    class DefaultOperationMutation(DjangoFormMutation):
        form_output_json = graphene.String()
        class Meta:
            form_class = form_klass

        @classmethod
        def perform_mutate(cls, form, info):
            return cls(errors=[], from_output_json=json.dumps(form.execute_func()))


    DefaultOperationMutation.__doc__ = f'Mutation form for {form_klass.__name__}.\n{form_klass.__doc__}'
    DefaultOperationMutation.__name__ = f'{form_klass.__name__}Mutation'
    return DefaultOperationMutation
