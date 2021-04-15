import json
import graphene
from graphene_django.forms.mutation import DjangoFormMutation
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from graphene import relay
from . import models
from graphene_django.forms import converter as graphene_django_converter
from django import forms
from . import utils

# PATCH IT GOOD!
import turtle_shell.graphene_adapter_jsonstring

# TODO: (try/except here with pydantic)
from turtle_shell import pydantic_adapter


_seen_names: set = set()

# class FakeJSONModule:
#     @classmethod
#     def loads(self, *a, **k):
#         return json.loads(*a, **k)
#
#     @classmethod
#     def dumps(self, *a, **k):
#         k['cls'] = utils.EnumAwareEncoder
#         return json.dumps(*a, **k)
#
#     @classmethod
#     def dump(self, *a, **k):
#         k['cls'] = utils.EnumAwareEncoder
#         return json.dump(*a, **k)
#
# import graphene_django.views
# import graphene.types.json
#
# graphene_django.views.json = FakeJSONModule
# graphene.types.json.json = FakeJSONModule


@graphene_django_converter.convert_form_field.register(forms.TypedChoiceField)
def convert_form_field_to_choice(field):
    # TODO: this should really be ported back to graphene django
    from graphene_django.converter import convert_choice_field_to_enum

    name = full_name = f"{field._func_name}{field._parameter_name}"
    index = 0
    while full_name in _seen_names:
        index += 1
        full_name = f"{name}{index}"
    EnumCls = convert_choice_field_to_enum(field, name=full_name)
    print(EnumCls, getattr(EnumCls, "BAM", None))
    converted = EnumCls(description=field.help_text, required=field.required)
    _seen_names.add(full_name)

    return converted


class ExecutionResult(DjangoObjectType):
    class Meta:
        model = models.ExecutionResult
        interfaces = (relay.Node,)
        filter_fields = {
            "func_name": ["exact"],
            "uuid": ["exact"],
        }
        fields = [
            "uuid",
            "func_name",
            "status",
            "input_json",
            "output_json",
            "error_json",
            "created",
            "modified",
            # TODO: will need this to be set up better
            # "user"
        ]


def func_to_graphene_form_mutation(func_object):
    form_class = func_object.form_class
    defaults = getattr(func_object.form_class, "_input_defaults", None) or {}

    class Meta:
        form_class = func_object.form_class

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        """Set defaults from function in place!"""
        input = {**defaults, **input}
        print(
            f"MUTATE GET PAYLOAD {input} {repr(input.get('read_type'))} {type(input.get('read_type'))}"
        )
        form = cls.get_form(root, info, **input)
        if not form.is_valid():
            print(form.errors)
        try:
            return super(DefaultOperationMutation, cls).mutate_and_get_payload(root, info, **input)
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise

    @classmethod
    def perform_mutate(cls, form, info):
        obj = form.save()
        all_results = obj.execute()
        obj.save()
        kwargs = {"execution": obj}
        if hasattr(all_results, "dict"):
            for k, f in fields.items():
                if k != "execution":
                    kwargs[k] = all_results
        # TODO: nicer structure
        if obj.error_json:
            message = obj.error_json.get("message") or "Hit error in execution :("
            errors = [{"message": message, "extensions": obj.error_json}]
        else:
            errors = []

        return cls(errors=errors, **kwargs)

    # TODO: figure out if name can be customized in class
    mutation_name = f"{form_class.__name__}Mutation"
    fields = {"execution": graphene.Field(ExecutionResult)}
    pydantic_adapter.maybe_add_pydantic_fields(func_object, fields)
    DefaultOperationMutation = type(
        mutation_name,
        (DjangoFormMutation,),
        (
            {
                **fields,
                "Meta": Meta,
                "perform_mutate": perform_mutate,
                "__doc__": f"Mutation form for {form_class.__name__}.\n{form_class.__doc__}",
                "mutate_and_get_payload": mutate_and_get_payload,
            }
        ),
    )
    return DefaultOperationMutation


def schema_for_registry(registry):
    # TODO: make this more flexible!
    class Query(graphene.ObjectType):
        execution_results = DjangoFilterConnectionField(ExecutionResult)
        execution_result = graphene.Field(ExecutionResult, uuid=graphene.String())

        def resolve_execution_result(cls, info, uuid):
            try:
                return models.ExecutionResult.objects.get(pk=uuid)
            except models.ExecutionResult.DoesNotExist:
                pass

    mutation_fields = {}
    for func_obj in registry.func_name2func.values():
        mutation = func_to_graphene_form_mutation(func_obj)
        mutation_fields[f"execute_{func_obj.name}"] = mutation.Field()
    Mutation = type("Mutation", (graphene.ObjectType,), mutation_fields)
    return graphene.Schema(query=Query, mutation=Mutation)
