from .utils import execute_gql, execute_gql_and_get_input_json
import turtle_shell
from turtle_shell import utils
import enum
import pytest


@pytest.mark.django_db
class TestDefaultHandling:
    def test_defaults(db):
        # defaults should be passed through
        def myfunc(a: bool = True, b: str = "whatever"):
            pass

        resp = execute_gql_and_get_input_json(
            myfunc, "mutation { executeMyfunc(input: {}) { result { inputJson }}}"
        )
        assert resp == {"a": True, "b": "whatever"}

    def test_enum_preservation(db):
        class ReadType(enum.Enum):
            fastq = enum.auto()
            bam = enum.auto()

        def func(read_type: ReadType = ReadType.fastq):
            return read_type

        input_json = execute_gql_and_get_input_json(
            func, "mutation { executeFunc(input: {readType: BAM}) { result { inputJson }}}"
        )
        assert input_json == {"read_type": utils.EnumRegistry.to_json_repr(ReadType.bam)}
        assert input_json["read_type"]["__enum__"]["name"] == "bam"

        input_json = execute_gql_and_get_input_json(
            func, "mutation { executeFunc(input: {}) { result { inputJson }}}"
        )
        assert input_json == {"read_type": utils.EnumRegistry.to_json_repr(ReadType.fastq)}
        assert input_json["read_type"]["__enum__"]["name"] == "fastq"

    def test_default_none(db):

        # defaults should be passed through
        def myfunc(a: bool = None, b: str = None):
            pass

        resp = execute_gql_and_get_input_json(
            myfunc, "mutation { executeMyfunc(input: {}) { result { inputJson }}}"
        )
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

    def test_rendering_enum_with_mixed_type(db):
        class MiscStringEnum(enum.Enum):
            whatever = "bobiswhatever"
            mish = "dish"
            defa = "default yeah"

        def func(s: MiscStringEnum = MiscStringEnum.defa):
            return s

        input_json = execute_gql_and_get_input_json(
            func, "mutation { executeFunc(input: {}) { result { inputJson }}}"
        )
        input_json2 = execute_gql_and_get_input_json(
            func, "mutation { executeFunc(input: {s: DEFAULT_YEAH}) { result { inputJson }}}"
        )
        assert input_json == input_json2
