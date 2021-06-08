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
    ...     get_docs = collection_resource('docs', Document)

This creates a resouce object that can be traversed at the item name 'docs'
that can be used to manage the ORM objects from the table ``document``. We
only need to give the resource tree a ``db_session`` that can be discovered
using the ``ctq.acqurie`` method.::

    >>> site = Site()
    >>> site.db_session = create_session()
    >>> site['docs']
    <ctq_sqlalchemy.collection.Docs ...>

This collection object implements some of the standard syntax that you would
use with SQLAlchemy. Namly ``select()`` and ``execute()``

Select returns a selectable from SQLAlchemy with the ORM object already selected.
``execute()`` returns an iterator which yields the ORM objects from ``select()``
bound to the collection object.

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
    <ctq_sqlalchemy.collection.Docs ...>
    >>> doc.__parent__.__parent__
    <Site ...>