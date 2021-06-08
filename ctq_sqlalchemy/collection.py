from ctq import acquire
from ctq import resource

import sqlalchemy


def collection_resource(name, child_type, **kwargs):
    type_name = normalise_type_name(name)
    collection_type = type(  # Construct an anonymous class
        type_name,
        (Collection,),
        {
            "child_type": child_type,
            **kwargs,
        },
    )
    resource_property = resource(name)(collection_type)
    return resource_property


def normalise_type_name(name):
    parts = name.replace("-", "_").split("_")
    name = "".join(p.title() for p in parts)
    return "ctq_sqlalchemy.collection.anonymous." + name


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
        name_from_child = self.parent.name_from_child
        for row in self.inner_result:
            child = row[0]
            child.__parent__ = self.parent
            name = name_from_child(child)
            if name:
                child.__name__ = name
