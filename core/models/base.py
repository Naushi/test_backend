import uuid
from datetime import datetime

from flask import abort, g
from flask_sqlalchemy import BaseQuery, SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils import UUIDType


class Query(BaseQuery):
    def one_or_404(self):
        try:
            return self.one()

        except NoResultFound:
            message = "No found."

            entity = self._entity_zero()

            if entity is not None:
                message = f"{entity.class_.__name__} not found."
            return abort(404, message)

    def joinload(self, *props, **kwargs):
        alias = kwargs.pop("alias", None)
        outer = kwargs.pop("outer", True)
        load = kwargs.pop("load", True)
        path = kwargs.pop("path", None)

        joins = props if alias is None else (alias,) + props

        query = getattr(self, "outerjoin" if outer else "join")(*joins, **kwargs)

        if load:
            if path is None:
                path = props

            load_option = contains_eager(*path, alias=alias)
            query = query.options(load_option)

        return query


db = SQLAlchemy(session_options={"expire_on_commit": False})


session = db.session


class GUID(UUIDType):
    pass


class Model(db.Model):
    __abstract__ = True
    _indexes_registry = dict()

    query_class = Query

    def save(self):
        session.add(self)
        if not g.get("already_flushing"):
            session.flush()
        return self

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        if not g.get("already_flushing"):
            session.flush()
        return self

    def delete(self):
        session.delete(self)

        session.flush()
        return self

    @classmethod
    def get_schema(cls, *args, **kwargs):
        schema_class = getattr(cls, "schema_class", None)

        if schema_class is None:
            raise NotImplementedError(f"`{cls.__name__}.schema_class` is not defined.")

        return schema_class(*args, **kwargs)

    def serialize(self, schema=None):
        if schema is None:
            schema = self.get_schema()

        return schema.dump(self, update_fields=False).data

    repr_attributes = tuple()

    def __repr__(self):
        identity = inspect(self).identity

        if identity is None:
            pk = "(transient {})".format(id(self))

        else:
            pk = ", ".join(str(value) for value in identity)

        values = dict(id=pk)

        values.update({key: getattr(self, key) for key in self.repr_attributes})

        return "<%s %s>" % (
            self.__class__.__name__,
            " ".join([f"{key}={value}" for key, value in values.items()]),
        )


class TimeStampMixin:
    __updatable__ = True

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @declared_attr
    def updated_at(cls):
        if cls.__updatable__:
            return db.Column(db.DateTime, onupdate=datetime.utcnow)


class IntegerPK(Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)


class GUIDPk(Model):
    __abstract__ = True

    id = db.Column(GUID, primary_key=True, default=uuid.uuid4, nullable=False)
