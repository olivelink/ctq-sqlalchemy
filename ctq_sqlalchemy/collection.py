from ctq import acquire
from ctq import resource

import sqlalchemy
import sqlalchemy_utils.types


def collection_resource(name, child_type, **kwargs):

    collection_type = type(  # Construct an anonymous class
        _normalise_type_name(name),
        (Collection,),
        {
            "child_type": child_type,
            "name_from_child": _name_from_child_method(child_type),
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
    field = primary_key[0]
    type_ = field.type
    if isinstance(type_, sqlalchemy.types.String):
        cast = str
    elif isinstance(type_, sqlalchemy_utils.types.uuid.UUIDType):
        cast = UUID
    elif isinstance(type_, sqlalchemy.types.Integer):
        cast = str
    else:
        NotImplementedError()

    def name_from_child(self, child):
        value = getattr(child, field.name)
        return cast(value)

    return name_from_child

class Collection(object):

    child_type = None

    def select(self):
        return sqlalchemy.select(self.child_type)

    def execute(self, stmt):
        session = acquire(self).db_session
        result = session.execute(stmt)
        wrapped_results = CollectionResultWrapper(result, self)
        return wrapped_results

    


class CollectionResultWrapper(object):
    def __init__(self, result, collection: Collection):
        self.inner_result = result
        self.collection = collection

    def __iter__(self):
        name_from_child = self.collection.name_from_child
        for row in self.inner_result:
            child = row[0]
            child.__parent__ = self.collection
            name = name_from_child(child)
            if name:
                child.__name__ = name
            yield child
