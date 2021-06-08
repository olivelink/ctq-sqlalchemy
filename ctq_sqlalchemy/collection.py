from ctq import acquire
from ctq import resource_path_names

import sqlalchemy




class Collection(object):

    child_type = None
    default_order_by = None

    def select(self):
        return sqlalchemy.select(self.child_type)

    def select_ordered(self):
        return (
            self.select()
            .order_by(self.default_order_by)
        )

    def execute(self, stmt):
        session = acquire(self).db_session
        result = session.execute(stmt)
        wrapped_results = CollectionResultWrapper(result, self)
        return wrapped_results

    def get_child(self, name, default=None):
        id = self.id_from_name(name)
        stmt = (
            self.select()
            .filter_by(**id)
        )
        result = self.execute(stmt).one_or_none()
        if result is None:
            return default
        return result

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except (KeyError, AttributeError) as err:
            child_path_names = resource_path_names(self) + (key,)
            try:
                cached_child = acquire(self).resource_cache_get(child_path_names)
            except AttributeError:
                cached_child = None
            if cached_child is not None:
                return cached_child
            child = self.get_child(key)
            if child is not None:
                try:
                    acquire(self).resource_cache_set(child_path_names, child)
                except AttributeError:
                    pass
                return child
            raise KeyError(key) from err
    

class CollectionResultWrapper(object):
    def __init__(self, result, collection: Collection):
        self.inner_result = result
        self.collection = collection

    def __iter__(self):
        name_from_child = self.collection.name_from_child
        for row in self.inner_result:
            child = row[0]
            self.bind(child)
            yield child
    
    def one_or_none(self):
        result = self.inner_result.one_or_none()
        if result is None:
            return None
        child = result[0]
        self.bind(child)
        return child

    def bind(self, child):
        child.__parent__ = self.collection
        name = self.collection.name_from_child(child)
        if name:
            child.__name__ = name
