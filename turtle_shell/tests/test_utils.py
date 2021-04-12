from turtle_shell import utils
import enum
import json
import pytest

def test_json_encoder_not_registered():
    class MyEnum(enum.Enum):
        a = enum.auto()

    with pytest.raises(TypeError, match="has not been registered"):
        json.dumps(MyEnum.a, cls=utils.EnumAwareEncoder)

def test_json_encoder_registered():
    class MyOtherEnum(enum.Enum):
        a = enum.auto()

    utils.EnumRegistry.register(MyOtherEnum)

    original = {"val": MyOtherEnum.a}
    s = json.dumps(original, cls=utils.EnumAwareEncoder)
    assert '"__enum__"' in s
    round_trip = json.loads(s, cls=utils.EnumAwareDecoder)
    assert round_trip == original

