import re
import slugify
from collections import OrderedDict

from sqlalchemy import cast
from sqlalchemy.types import SchemaType, TypeDecorator, Enum
from sqlalchemy.dialects.postgresql import ARRAY


class EnumSymbol(object):
    """Define a fixed symbol tied to a parent class."""

    def __init__(self, cls_, name, value, description, extras=None):
        self.cls_ = cls_
        self.name = name
        self.value = value
        self.description = description
        self.extras = extras

    @property
    def slug(self):
        return slugify.slugify(str(self.description))

    def __reduce__(self):
        """Allow unpickling to return the symbol
        linked to the DeclEnum class."""
        return getattr, (self.cls_, self.name)

    def __iter__(self):
        return iter([self.value, self.description])

    def __repr__(self):
        return "<%s>" % self.name

    def __str__(self):
        return str(self.description)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            other == other.value

        return self.value == other

    def __hash__(self):
        return hash(self.value)

    def to_dict(self):
        data = dict(name=self.name, label=self.description)
        extras = self.extras

        if extras is not None:
            data.update(extras._asdict())

        return data


class EnumMeta(type):
    """Generate new DeclEnum classes."""

    def __init__(cls, classname, bases, dict_):
        cls._reg = reg = cls._reg.copy()

        for k, v in dict_.items():
            if isinstance(v, tuple):
                sym = reg[v[0]] = EnumSymbol(cls, k, *v)
                setattr(cls, k, sym)
        return type.__init__(cls, classname, bases, dict_)

    @classmethod
    def __prepare__(mcl, name, bases):
        return OrderedDict()

    def __iter__(cls):
        return iter(cls._reg.values())


def to_underscore(name):
    return re.sub(r"(?!^)([A-Z]+)", r"_\1", name).lower()


class DeclEnum(metaclass=EnumMeta):
    """Declarative enumeration."""

    _reg = OrderedDict()

    @classmethod
    def _from_registry(cls, reg, key):
        try:
            return reg[key]
        except KeyError:
            raise ValueError("Invalid value for %r: %r" % (cls.__name__, key))

    @classmethod
    def from_string(cls, value):
        return cls._from_registry(cls._reg, value)

    @classmethod
    def from_slug(cls, slug):
        for value in cls._reg.items():
            if value[1].slug == slug:
                return value[1]

        raise ValueError(f"`{slug}` not found")

    @classmethod
    def values(cls):
        return cls._reg.keys()

    @classmethod
    def db_type(cls):
        return DeclEnumType(cls)

    @classmethod
    def choices(cls):
        return [(str(key), str(value)) for key, value in cls._reg.items()]


class DeclEnumType(SchemaType, TypeDecorator):
    def __init__(self, enum):
        self.enum = enum
        self.impl = Enum(*enum.values(), name=to_underscore(enum.__name__))

    def _set_table(self, table, column):
        self.impl._set_table(table, column)

    def copy(self):
        return DeclEnumType(self.enum)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if isinstance(value, str):
            return value

        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        return self.enum.from_string(value.strip())

    python_type = str


class EnumArray(ARRAY):
    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)

    def result_processor(self, dialect, coltype):
        processor = super().result_processor(dialect, coltype)

        def handle_raw_string(value):
            inner = re.match(r"^{(.*)}$", value).group(1)
            return inner.split(",") if inner else []

        def process(value):
            if value is None:
                return None

            return processor(handle_raw_string(value))

        return process

    @property
    def enums(self):
        return self.item_type.enums
