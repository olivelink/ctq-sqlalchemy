from sqlalchemy.sql.schema import PrimaryKeyConstraint
from ctq import acquire
from ctq import resource_path_names
from ctq import emit

import sqlalchemy


class CollectionBase(object):

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

    def __iter__(self):
        stmt = self.select()
        for item in self.execute(stmt):
            yield item
    
    def add(self, _name=None, /, **kwargs):
        if _name is not None:
            kwargs = {
                **self.id_from_name(_name),
                **kwargs
            }
        emit(self, "before-add", {"kwargs": kwargs})
        child = self.child_type(**kwargs)
        acquire(self).db_session.add(child)
        child.__parent__ = self
        name = self.name_from_child(child)
        child.__name__ = name
        child_path_names = resource_path_names(child)
        try:
            acquire(self).resource_cache_set(child_path_names, child)
        except AttributeError:
            pass
        emit(child, "after-add")
        return child

    def __delitem__(self, key):
        child = self[key]
        child_path_names = resource_path_names(child)
        emit(child, "before-delete")
        try:
            acquire(self).resource_cache_set(child_path_names, None)
        except AttributeError:
            pass
        acquire(self).db_session.delete(child)
        emit(self, "after-delete", {"path": child_path_names})
    
    def edit(self, child, **kwargs):
        old_name = self.name_from_child(child)
        emit(child, "before-edit", {"kwargs": kwargs})
        changes = {}
        for key, value in kwargs.items():
            old_value = getattr(child, key)
            if old_value != value:
                changes[key] = {
                    "old": old_value,
                    "new": value,
                }
                setattr(child, key, value)
        name = self.name_from_child(child)
        child.__name__ = name
        if old_name != name:
            base_path_names = resource_path_names(self)
            old_path_names = base_path_names + (old_name,)
            path_names = base_path_names + (name,)
            try:
                resource_cache_set = acquire(self).resource_cache_set
                resource_cache_set(old_path_names, None)
                resource_cache_set(path_names, child)
            except AttributeError:
                pass
            emit(child, "moved", {
                "old_path": old_path_names,
            })
        emit(child, "after-edit", {
            "kwargs": kwargs,
            "changes": changes,
        })
    
    def rename(self, child, name):
        id = self.id_from_name(name)
        self.edit(child, **id)

class CollectionResultWrapper(object):
    def __init__(self, result, collection: CollectionBase):
        self.inner_result = result
        self.collection = collection
        self.name_from_child = collection.name_from_child
        self.cache_get = getattr(acquire(collection), "resource_cache_get", self.cache_get)
        self.cache_set = getattr(acquire(collection), "resource_cache_set", self.cache_set)
        self.collection_path_names = resource_path_names(collection)

    def __iter__(self):
        name_from_child = self.collection.name_from_child
        for row in self.inner_result:
            child = self.child_from_row(row)
            yield child
    
    def one_or_none(self):
        row = self.inner_result.one_or_none()
        if row is None:
            return None
        return self.child_from_row(row)

    def child_from_row(self, row):
        child = row[0]
        child.__parent__ = self.collection
        name = self.name_from_child(child)
        if name is not None:
            child_path_names = self.collection_path_names + (name,)
            cached_child = self.cache_get(child_path_names)
            if cached_child is not None:
                return cached_child
            child.__name__= name
            self.cache_set(child_path_names, child)
            return child
        else:
            return child

    def cache_get(self, key):
        return None

    def cache_set(self, key, value):
        pass