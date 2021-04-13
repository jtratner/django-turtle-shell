"""Patch graphene django's JSONString implementation so we can use a custom encoder"""
# Port over of graphene's JSON string to allow using a custom encoder...sigh
import json

from graphql.language import ast

from graphene.types.scalars import Scalar


class CustomEncoderJSONString(Scalar):
    """
    Allows use of a JSON String for input / output from the GraphQL schema.

    Use of this type is *not recommended* as you lose the benefits of having a defined, static
    schema (one of the key benefits of GraphQL).
    """

    @staticmethod
    def serialize(dt):
        from turtle_shell import utils

        return json.dumps(dt, cls=utils.EnumAwareEncoder)

    @staticmethod
    def parse_literal(node):
        if isinstance(node, ast.StringValue):
            return json.loads(node.value)

    @staticmethod
    def parse_value(value):
        return json.loads(value)


from graphene_django import converter

converter.JSONString = CustomEncoderJSONString
