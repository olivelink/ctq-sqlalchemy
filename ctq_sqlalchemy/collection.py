from .collection_base import CollectionBase
from functools import cached_property
from ctq import ResourceCache
from ctq import resource
from uuid import UUID

import sqlalchemy_utils.types
import sqlalchemy


class CollectionType(type):

    def __new__(mcs, name, bases, content):
        bases = (*bases, CollectionBase)

        child_type = content["child_type"]
        assert child_type is not None
        primary_key = sqlalchemy.inspect(child_type).primary_key
        name_from_child = generate_name_from_child_method(primary_key)
        id_from_name = generate_id_from_name_method(primary_key)
        content = {
            "_primary_key": primary_key,
            "_default_order_by": primary_key,
            "name_from_child": name_from_child,
            "id_from_name": id_from_name,
            **content
        }
        return type.__new__(mcs, name, bases, content)


def collection_resource(name, child_type, cache_max_size=0, **kwargs):

    # Calculate name
    name_parts = name.replace("-", "_").split("_")
    klass_name = "".join(p.title() for p in name_parts)

    bases = ()
    content = {
        "child_type": child_type,
        **kwargs,
    }
    if cache_max_size > 0:
        bases = (ResourceCache,)
        content["resource_cache_max_size"] = cache_max_size

    klass = CollectionType(klass_name, bases, content)

    factory = lambda self: klass()
    resource_property = resource(name)(factory)
    return resource_property


def generate_name_from_child_method(primary_key):
    assert len(primary_key) == 1
    
    def name_from_child(self, child):
        value = getattr(child, primary_key[0].name)
        return str(value)

    return name_from_child


def generate_id_from_name_method(primary_key):
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