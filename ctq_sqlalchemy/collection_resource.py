from .collection import Collection
from ctq import resource
from uuid import UUID

import sqlalchemy
import sqlalchemy_utils.types


def collection_resource(name, child_type, **kwargs):

    collection_type = type(  # Construct an anonymous class
        _normalise_type_name(name),
        (Collection,),
        {
            "child_type": child_type,
            "name_from_child": _name_from_child_method(child_type),
            "id_from_name": _id_from_name_method(child_type),
            **kwargs,
        },
    )
    factory = lambda self: collection_type()
    resource_property = resource(name)(factory)
    return resource_property


def _normalise_type_name(name):
    parts = name.replace("-", "_").split("_")
    name = "".join(p.title() for p in parts)
    return name

def _name_from_child_method(child_type):
    primary_key = sqlalchemy.inspect(child_type).primary_key
    assert len(primary_key) == 1
    
    def name_from_child(self, child):
        value = getattr(child, primary_key[0].name)
        return str(value)

    return name_from_child

def _id_from_name_method(child_type):
    primary_key = sqlalchemy.inspect(child_type).primary_key
    assert len(primary_key) == 1
    field = primary_key[0]
    type_ = field.type
    if isinstance(type_, sqlalchemy.types.String):
        cast = str
    elif isinstance(type_, sqlalchemy_utils.types.uuid.UUIDType):
        cast = UUID
    elif isinstance(type_, sqlalchemy.types.Integer):
        cast = int
    else:
        NotImplementedError()

    def id_from_name(self, name):
        return {
            field.name: cast(name),
        }

    return id_from_name