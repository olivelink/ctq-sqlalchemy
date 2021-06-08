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
    ...     body = sqlalchemy.Column(sqlalchemy.Unicode)

    >>> db_engine = sqlalchemy.create_engine("sqlite://")
    >>> Base.metadata.create_all(db_engine)
    >>> create_session = sqlalchemy.orm.session.sessionmaker(bind=db_engine)

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
using the ``ctq.acqurie`` method.

    ... site = Site()
    ... site.db_session = create_session()
    ... site['docs']
    <ctq_sqlalchemy.collection.anonymous.Document ...>