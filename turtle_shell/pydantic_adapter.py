"""
Pydantic model handling!

This module is designed to be a conditional import with fake pydantic instead used if pydantic not
available.
"""
import typing
from graphene_pydantic import PydanticObjectType, registry
from pydantic import BaseModel
import inspect
import graphene
import logging

logger = logging.getLogger(__name__)


def is_pydantic(func):
    ret_type = inspect.signature(func).return_annotation
    if args := typing.get_args(ret_type):
        ret_type = args[0]
    return inspect.isclass(ret_type) and issubclass(ret_type, BaseModel) and ret_type


def get_pydantic_models_in_order(model):
    """Get all nested models in order for definition"""
    found = []
    for field in model.__fields__.values():
        type_ = field.type_
        if issubclass(type_, BaseModel):
            found.extend(get_pydantic_models_in_order(type_))
    found.append(model)
    seen_classes = set()
    deduped = []
    for elem in found:
        if elem not in seen_classes:
            deduped.append(elem)
            seen_classes.add(elem)
    return deduped


def get_object_type(model) -> PydanticObjectType:
    """Construct object types in order, using caching etc"""
    reg = registry.get_global_registry()
    classes = get_pydantic_models_in_order(model)
    for klass in classes:
        if reg.get_type_for_model(klass):
            continue

        pydantic_oject = type(
            klass.__name__,
            (PydanticObjectType,),
            {"Meta": type("Meta", (object,), {"model": klass})},
        )
        assert reg.get_type_for_model(klass), klass
    return reg.get_type_for_model(model)


def maybe_add_pydantic_fields(func_object, fields):
    if not (pydantic_class := is_pydantic(func_object.func)):
        return
    obj_name = pydantic_class.__name__

    root_object = get_object_type(pydantic_class)
    fields[obj_name[0].lower() + obj_name[1:]] = graphene.Field(root_object)


def maybe_convert_pydantic_model(result):
    if isinstance(result, BaseModel):
        return result.dict()
    return result


def get_pydantic_object(execution_result):
    func = execution_result.get_function()
    if ret_type := is_pydantic(func):
        try:
            return ret_type.parse_obj(execution_result.output_json)
        except Exception as e:
            logger.warn(f"Hit exception unparsing {type(e).__name__}{e}", exc_info=True)
