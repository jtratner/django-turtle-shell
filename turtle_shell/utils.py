import json
import enum
from collections import defaultdict
from django.core.serializers.json import DjangoJSONEncoder

class EnumRegistry:
    # URP - global! :(
    _registered_enums = defaultdict(dict)

    @classmethod
    def register(cls, enum_class):
        cls._registered_enums[enum_class.__module__][enum_class.__qualname__] = enum_class

    @classmethod
    def has_enum(cls, enum_class):
        try:
            return cls._registered_enums[enum_class.__module__][enum_class.__qualname__]
        except KeyError:
            return None

    @classmethod
    def to_json_repr(cls, enum_member):
        if not cls.has_enum(type(enum_member)):
            raise TypeError(f"Enum type {type(enum_member)} has not been registered and can't be serialized :(")
        enum_class = type(enum_member)
        return {"__enum__": {"__type__": [enum_class.__module__, enum_class.__qualname__], "name": enum_member.name, "value": enum_member.value}}

    @classmethod
    def from_json_repr(cls, json_obj):
        if "__enum__" not in json_obj:
            raise ValueError("Enums must be represented by __enum__ key")
        try:
            type_data = json_obj["__enum__"]["__type__"]
            try:
                enum_class = cls._registered_enums[type_data[0]][type_data[1]]
            except KeyError:
                raise ValueError(f"Looks like enum {type_data} is not registered :(")
            return enum_class(json_obj["__enum__"]["value"])
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid enum representation in JSON:: {type(e).__name__}: {e}")

    @classmethod
    def object_hook(cls, dct):
        if '__enum__' not in dct:
            return dct
        return cls.from_json_repr(dct)


class EnumAwareEncoder(DjangoJSONEncoder):
    def default(self, o, **k):
        if isinstance(o, enum.Enum):
            return EnumRegistry.to_json_repr(o)
        else:
            super().default(o, **k)

class EnumAwareDecoder(json.JSONDecoder):
    def __init__(self, *a, **k):
        k.setdefault('object_hook', self.object_hook)
        super().__init__(*a, **k)

    def object_hook(self, dct):
        return EnumRegistry.object_hook(dct)
