from .collection_base import CollectionBase
from functools import cached_property
from ctq import ResourceCache
from ctq import resource
from uuid import UUID

import sqlalchemy_utils.types
import sqlalchemy
import dateutil.parser


class CollectionType(type):

    def __new__(mcs, name, bases, content):
        for base in bases:
            if issubclass(base, CollectionBase):
                return type.__new__(mcs, name, bases, content)

        bases = (*bases, CollectionBase)

        child_type = content["child_type"]
        assert child_type is not None

        more_content = {}

        insp = sqlalchemy.inspect(child_type)
        primary_key = insp.primary_key

        if "default_order_by" not in content:
            more_content["default_order_by"] = primary_key

        # Get or detect a "key" column
        key_column = content.get("key", None)
        if key_column is None and len(primary_key) == 1:
            key_column = primary_key[0]
            key_column = insp.get_property_by_column(key_column)
            more_content["key"] = key_column

        if key_column is not None:
            key_attr_name = key_column.key
            key_column = getattr(child_type, key_attr_name)

            # Create a name_from_child method
            more_content["name_from_child"] = generate_name_from_child_method(key_column, key_attr_name)

            # If there is only 1 primary key then generate id_from_name
            if len(primary_key) == 1:
                more_content["id_from_name"] = generate_id_from_name_method(
                    key_column,
                    key_attr_name,
                )

        content = {
            **more_content,
            **content,
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


def generate_name_from_child_method(field, key_attr_name):
    to_str = str
    type_ = field.type
    if isinstance(type_, sqlalchemy.types.DateTime):
        to_str = lambda o: o.isoformat()
    def name_from_child(self, _child=None, /, **overrides):
        value = overrides.get(key_attr_name) or getattr(_child, key_attr_name)
        if value is None:  # Don't set names from None values. This is possible during init adding of an item.
            return None
        return to_str(value)

    return name_from_child


def generate_id_from_name_method(field, key_field_name):
    type_ = field.type
    if isinstance(type_, sqlalchemy.types.String):
        cast = str
    elif isinstance(type_, sqlalchemy_utils.types.uuid.UUIDType):
        cast = UUID
    elif isinstance(type_, sqlalchemy.types.Integer):
        cast = int
    elif isinstance(type_, sqlalchemy.types.DateTime):
        cast = dateutil.parser.isoparse
    else:
        NotImplementedError()

    def id_from_name(self, name):
        return {
            key_field_name: cast(name),
        }

    return id_from_name