ctq_sqlalchemy
==============


Let's start with a simple SQLAlchemy setup...


So lstart with a sqlalchemy ORM object.::

    >>> import sqlalchemy
    >>> from sqlalchemy.orm import declarative_base
    >>> Base = declarative_base()
    
    >>> class Document(Base):
    ...
    ...     __tablename__ = "document"
    ...
    ...     document_id = sqlalchemy.Column(sqlalchemy.Unicode, primary_key=True)
    ...     title = sqlalchemy.Column(sqlalchemy.Unicode)

    >>> db_engine = sqlalchemy.create_engine("sqlite://")
    >>> Base.metadata.create_all(db_engine)
    >>> create_session = sqlalchemy.orm.session.sessionmaker(bind=db_engine)

And lets populate it with at least one Document

    >>> db_session = create_session()
    >>> intro_doc = Document(document_id="intro", title="Welcome...")
    >>> conclusion_doc = Document(document_id="conclusion", title="Summing up...")
    >>> db_session.add(intro_doc)
    >>> db_session.add(conclusion_doc)
    >>> db_session.commit()

We can create a site object with a collection of these documents using the
``collection_resource`` property constructer with a class that inherts from
``ctq.Resourceful``::

    >>> from ctq import Resourceful
    >>> from ctq_sqlalchemy import collection_resource
    
    >>> class Site(Resourceful):
    ...
    ...     get_docs = collection_resource('docs', Document, cache_max_size=100)

This creates a resouce object that can be traversed at the item name 'docs'
that can be used to manage the ORM objects from the table ``document``. We
only need to give the resource tree a ``db_session`` that can be discovered
using the ``ctq.acqurie`` method.::

    >>> site = Site()
    >>> site.db_session = create_session()
    >>> site['docs']
    <ctq_sqlalchemy.collection_resource.Docs ...>

This collection object implements some of the standard syntax that you would
use with SQLAlchemy. Namly ``select()`` and ``execute()``

Select returns a selectable from SQLAlchemy with the ORM object already selected.
``execute()`` returns an iterator which yields the ORM objects from ``select()``
bound to the collection object.::

    >>> docs = site['docs']
    >>> stmt = docs.select().where(Document.document_id == 'intro')
    >>> items = list(docs.execute(stmt))
    >>> assert len(items) == 1 
    >>> doc = items[0]
    >>> doc.title
    'Welcome...'
    >>> doc.__name__
    'intro'
    >>> doc.__parent__
    <ctq_sqlalchemy.collection_resource.Docs ...>
    >>> doc.__parent__.__parent__
    <Site ...>

Because ctq-sqlalchemy auto detects the primary key of the object the items
also become traversable::

    >>> site['docs']['intro']
    <Document ...>
    >>> site['docs']['conclusion'].title
    'Summing up...'

The collection object has a convienence method ``add(...)`` which allows creating
new objects quickly.::

    >>> story = docs.add("story", title="First Story")
    >>> story.title
    'First Story'
    >>> story is docs['story']
    True
    >>> site.db_session.commit()

The collection object also supports the del operation in python.

    >>> site = Site()
    >>> site.db_session = create_session()
    >>> docs = site['docs']
    >>> del docs['story']
    >>> docs['story']
    Traceback (most recent call last):
    ...
    KeyError: 'story'

Now to editing. ctq-sqlalchemy support a range of events that are emited during
verious resource operations. Here is an example of using events with the
edit method on the collection.::

    >>> from ctq import handle

    >>> class Site(Resourceful):
    ...
    ...     get_docs = collection_resource('docs', Document, cache_max_size=100)
    ...
    ...     @handle("after-edit")
    ...     def on_after_edit(self, event):
    ...         print(f"{event.target.document_id} was edited! Changes: {event.data['changes']}")
    ...
    ...     @handle("moved")
    ...     def on_moved(self, event):
    ...         print(f"Resource was moved: from {event.data['old_path'][-1]} to {event.target.__name__}")
    ...
    
    >>> site = Site()
    >>> site.db_session = create_session()
    >>> docs = site['docs']
    >>> docs.edit(docs['intro'], title="Updated intro!")
    intro was edited! Changes: {'title': {'old': 'Welcome...', 'new': 'Updated intro!'}}
    >>> docs.edit(docs['intro'], document_id='introduction')
    Resource was moved: from intro to introduction
    introduction was edited! Changes: {'document_id': {'old': 'intro', 'new': 'introduction'}}

There is a convienence method ``rename`` which performes an edit based on primary key introspection.

    >>> docs.rename(docs['introduction'], "preface")
    Resource was moved: from introduction to preface
    preface was edited! Changes: {'document_id': {'old': 'introduction', 'new': 'preface'}}    

