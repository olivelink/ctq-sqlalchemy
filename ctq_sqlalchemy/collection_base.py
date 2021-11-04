from sqlalchemy.sql.schema import PrimaryKeyConstraint
from ctq import acquire
from ctq import resource_path_names
from ctq import emit
from uuid import UUID

import sqlalchemy
import datetime

class CollectionBase(object):

    child_type = None
    default_order_by = None

    def select(self):
        return sqlalchemy.select(self.child_type)

    def select_ordered(self):
        return (
            self.select()
            .order_by(*self.default_order_by)
        )

    def count(self, stmt=None):
        if stmt is None:
            stmt = self.select()
        stmt = sqlalchemy.select(sqlalchemy.func.count()).select_from(stmt.subquery())
        return acquire(self).db_session.execute(stmt).scalar()

    def execute(self, stmt):
        session = acquire(self).db_session
        result = session.execute(stmt)
        wrapped_results = CollectionResultWrapper(result, self)
        return wrapped_results

    def parent_for_child(self, child):
        return self

    def get_child(self, name, default=None):
        try:
            id = self.id_from_name(name)
        except (ValueError, TypeError):
            return default
        stmt = (
            self.select()
            .filter_by(**id)
        )
        result = self.execute(stmt).one_or_none()
        if result is None:
            return default
        return result

    def __getitem__(self, key):

        if not isinstance(key, str):
            # Only cast the nice things
            if not (
                isinstance(key, UUID)
                or isinstance(key, int)
                or isinstance(key, datetime.date)
            ):
                raise KeyError()
            key = str(key)

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
        stmt = stmt.execution_options(stream_results=True)
        result = self.execute(stmt)
        for partition in result.partitions(1000):
            for item in partition:
                yield item
    
    def add(self, _name=None, /, **kwargs):
        if _name is not None:
            kwargs = {
                **self.id_from_name(_name),
                **kwargs
            }

        child = self.child_type(**kwargs)

        # Set parent
        parent = self.parent_for_child(child)
        if parent:
            child.__parent__ = parent

        # Set name
        name = self.name_from_child(child)
        if name:
            child.__name__ = name

        # Emit event if there is a parent
        if parent:
            emit(child, "before-add", {"kwargs": kwargs})

        # Reset name
        name = self.name_from_child(child)  # recalculate name_from_child incase there are edits done during "before-add"
        if name:
            child.__name__ = name

        # add to session
        acquire(self).db_session.add(child)

        # Set cache if there is a parent and a name
        if parent and name is not None:
            child_path_names = resource_path_names(child)
            try:
                acquire(self).resource_cache_set(child_path_names, child)
            except AttributeError:
                pass
        
        # Emit event if there is a parent
        if parent:
            emit(child, "after-add", {"kwargs": kwargs})

        return child

    def merge(self, **kwargs):
        name = self.name_from_child(**kwargs)
        child = self.get_child(name)
        if child is None:
            return self.add(**kwargs)
        else:
            child.edit(**kwargs)
            return child

    def __delitem__(self, key):
        child = self[key]
        self.delete(child)

    def delete(self, child):
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

    def partitions(self, size):
        for partition in self.inner_result.partitions(size):
            yield self.iter_from_partition(partition)

    def iter_from_partition(self, partition):
        for row in partition:
            child = self.child_from_row(row)
            yield child

    def child_from_row(self, row):
        child = row[0]

        # Set parent
        parent = self.collection.parent_for_child(child)
        if parent:
            child.__parent__ = parent

        # Get a name
        name = self.name_from_child(child)
        child_path_names = None

        # Check cache
        if parent and name is not None:
            child_path_names = self.collection_path_names + (name,)
            cached_child = self.cache_get(child_path_names)
            if cached_child is not None:
                return cached_child

        # set name and set cache
        if name:
            child.__name__ = name
        if child_path_names is not None:
            self.cache_set(child_path_names, child)

        return child

    def cache_get(self, key):
        return None

    def cache_set(self, key, value):
        pass