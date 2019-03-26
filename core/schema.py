
import datetime
import logging
import uuid
from copy import copy

import schwifty
from flask import g, request, current_app
from pycountry import currencies
from marshmallow import post_load
from marshmallow.schema import Schema as BaseSchema
from marshmallow.fields import (
    DateTime as BaseDateTime,
    Date as BaseDate,
    Email,
    Function,
    List,
    Nested,
    String,
    Url as BaseUrl,
    Dict,
    UUID as BaseUUID,
)
from marshmallow.exceptions import ValidationError
from marshmallow_sqlalchemy import ModelSchema as BaseModelSchema
from marshmallow_sqlalchemy.convert import ModelConverter as BaseModelConverter
from marshmallow_sqlalchemy.schema import ModelSchemaOpts as BaseModelSchemaOpts
from phonenumbers import parse as parse_number, NumberParseException
from pycountry import countries
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils import EmailType, URLType, UUIDType
from sqlalchemy.dialects.postgresql import JSON

from core.dates import parse_iso_datetime, format_iso_datetime
from core.models.base import (
    GUID,
    Model,
    session as db_session,
)
from core.models.enum import DeclEnumType, EnumSymbol


logger = logging.getLogger(__name__)


class DateTime(BaseDateTime):
    def _deserialize(self, value, attr, data):
        if isinstance(value, datetime.datetime):
            return value

        value = value.replace("/", "-")

        try:
            return parse_iso_datetime(value, current_app.config["DEFAULT_TIMEZONE"])

        except ValueError:
            self.fail("invalid")


class OffsetDateTime(DateTime):
    def __init__(self, *args, **kwargs):
        self.get_timezone = kwargs.pop("timezone")
        super().__init__(*args, **kwargs)

    def _deserialize(self, value, attr, data):
        if isinstance(value, str):
            value = value.replace("Z", "")

        return super()._deserialize(value, attr, data)

    def _serialize(self, value, attribute, obj, *args):
        timezone = self.get_timezone(obj)
        return format_iso_datetime(value, timezone)


class Date(BaseDate):
    def _deserialize(self, value, attr, data):
        value = value.replace("/", "-")

        try:
            return datetime.datetime.strptime(value, "%Y-%m-%d").date()

        except ValueError:
            self.fail("invalid")


phone_number_messages = String.default_error_messages.copy()
phone_number_messages.update(
    dict(invalid=("Invalid number, must be sent in international format."))
)


class PhoneNumber(String):
    default_error_messages = phone_number_messages

    def _deserialize(self, value, attr, data):
        value = value.replace(" ", "")

        try:
            value = parse_number(value, "FR")

        except NumberParseException:
            raise self.fail("invalid")

        return f"+{value.country_code}{value.national_number}"


class Iban(String):
    """
    Specific field type with check on IBAN format
    """

    def _deserialize(self, value, attr, obj):
        try:
            return str(schwifty.IBAN(value))

        except ValueError as e:
            raise ValidationError(str(e))


class Bic(String):
    """
    Specific field type with check on BIC format
    """

    def _deserialize(self, value, attr, obj):
        try:
            return schwifty.BIC(value)

        except ValueError as e:
            raise ValidationError(str(e))


class Enum(String):
    def _serialize(self, value, *args):
        if isinstance(value, EnumSymbol):
            return str(value.value)

        return super()._serialize(value, *args)


class Country(String):
    """
    Specific field type with check on the validity of the country code format
    """

    def _deserialize(self, value, attr, obj):
        try:
            length = len(value)

            if length not in (2, 3):
                raise ValueError()

            kwargs = {f"alpha_{length}": value}
            country = countries.get(**kwargs)
            if not country:
                raise ValueError()
            return country.alpha_3

        except (ValueError, KeyError):
            raise ValidationError("Invalid country code.")


class PrefixedNested(Nested):
    """
    Merge nested schema to parent by prefixing fields key.
    """

    def clone_field(self, field):
        cloned_field = copy(field)
        cloned_field.required = self.required

        roles = field.metadata.get("roles", self.metadata.get("roles"))

        if roles is not None:
            cloned_field.metadata["roles"] = roles
            field.metadata["roles"] = roles

        return cloned_field

    @property
    def parent_fields(self):
        schema = self.schema
        prefix = self.prefix

        return {
            f"{prefix}_{key}": self.clone_field(field)
            for key, field in schema.fields.items()
        }

    def bind(self, parent, prefix, fields_dict):
        self.prefix = prefix
        fields_dict.update(self.parent_fields)

        del fields_dict[prefix]

        # Store `PrefixedNested` for later processing.
        if not hasattr(parent, "_prefixed"):
            parent._prefixed = {}

        parent._prefixed[prefix] = self


class Currency(String):
    """
    Currency ISO 4217 alpha 3
    """

    def _deserialize(self, value, attr, obj):
        try:
            currency = currencies.get(alpha_3=value)
            return currency.alpha_3

        except KeyError:
            raise ValidationError("Invalid currency.")


class PrefixedProcessingMixin:
    @post_load
    def process_prefixed(self, data):
        """
        Reconstruct nested data for prefixed fields.
        """
        prefixed = getattr(self, "_prefixed", dict())

        for field_name, field in prefixed.items():
            prefixed_data = dict()

            for root_field_name, root_field in field.parent_fields.items():
                value = data.pop(root_field_name, None)

                if value:
                    prefixed_data[root_field.name] = value

            if len(prefixed_data) > 0:
                schema = field.schema

                if hasattr(schema, "load_roles"):
                    schema.load_roles()

                data[field_name] = schema.load(prefixed_data).data

        return data


def get_class_by_table(table_name):
    """Return first class found mapped to given table.
    """
    for class_ in Model._decl_class_registry.values():
        if hasattr(class_, "__table__") and class_.__table__.fullname == table_name:
            return class_


class Url(BaseUrl):
    def deserialize(self, value, *args, **kwargs):
        if value == "":
            value = None

        return super().deserialize(value, *args, **kwargs)


class UUID(BaseUUID):
    def _deserialize(self, value, attr, obj):
        foreign_key = self.foreign_key
        validators = self.validators

        if foreign_key is not None and isinstance(value, dict):
            _value = value.get(foreign_key.key)
            value = _value if _value else value
        value = super()._deserialize(value, attr, obj)
        if foreign_key is not None and value is not None and len(validators) == 0:
            model = get_class_by_table(foreign_key.table.fullname)

            query = db_session.query(model).filter(foreign_key == str(value))

            try:
                with db_session.no_autoflush:
                    result = query.one()

                    if self.is_relationship:
                        return result

            except NoResultFound:
                raise ValidationError("Does not exist.")
        return value

    def _serialize(self, value, *args):
        if isinstance(value, Model):
            if self.embedded:
                if self._schema_class:
                    return self._schema_class().dump(value).data
                return value.serialize()

            value = value.id

        if value is None:
            return

        return str(value)


def deep_getattr(obj, path):
    parts = path.split(".")

    value = getattr(obj, parts[0])

    if value is None:
        return

    if len(parts) > 1:
        return deep_getattr(value, ".".join(parts[1:]))

    return value


def deep_setattr(obj, path, value):
    pre, _, post = path.rpartition(".")
    return setattr(deep_getattr(obj, pre) if pre else obj, post, value)


class ForeignField(Function):
    def __init__(self, *args, **kwargs):
        self.path = kwargs.pop("path")
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attribute, obj):
        obj = deep_getattr(obj, self.path)

        if isinstance(obj, list):
            objs = obj
            obj = []
            for o in objs:
                if hasattr(o, "serialize"):
                    obj.append(o.serialize())
                else:
                    obj.append(o)

        if hasattr(obj, "serialize"):
            return obj.serialize()

        return obj

    def populate_object(self, instance, value):
        deep_setattr(instance, self.path, value)


class Schema(PrefixedProcessingMixin, BaseSchema):
    pass


def __set_field_attrs(self, fields_dict):
    """
    Handle `PrefixedNested` fields binding.
    """
    for key, field in fields_dict.copy().items():
        if isinstance(field, PrefixedNested):
            field.bind(self, key, fields_dict)

    BaseSchema._BaseSchema__set_field_attrs(self, fields_dict)


Schema._BaseSchema__set_field_attrs = __set_field_attrs


model_type_mapping = Schema.TYPE_MAPPING.copy()

model_type_mapping.update(
    {datetime.datetime: DateTime, datetime.date: Date, uuid.uuid4: UUID, dict: Dict}
)


sqla_type_mapping = BaseModelConverter.SQLA_TYPE_MAPPING.copy()

sqla_type_mapping.update(
    {
        DeclEnumType: Enum,
        EmailType: Email,
        URLType: Url,
        UUIDType: UUID,
        GUID: UUID,
        JSON: Dict,
    }
)


def get_foreign_key_column(prop):
    """
    Checks if given property is either a relationship or a foreign
    key then returns `tuple(<is relationship>, <target column>, <target entity>)`.
    """
    if hasattr(prop, "direction"):
        target = prop.target
        columns = list(target.primary_key)
        if len(columns) == 1 and isinstance(columns[0].type, UUIDType):
            return True, columns[0], prop.mapper.entity

    columns = getattr(prop, "columns", [])

    if len(columns) == 1:
        column = columns[0]

        foreign_keys = getattr(column, "foreign_keys", set())

        if len(foreign_keys) == 1 and isinstance(column.type, UUIDType):
            # We're exposing a single column UUID foreign key.
            return False, foreign_keys.pop().column, None

    return False, None, None


class ModelConverter(BaseModelConverter):
    SQLA_TYPE_MAPPING = sqla_type_mapping

    def _add_column_kwargs(self, kwargs, column):
        if not hasattr(column, "nullable"):
            return

        super()._add_column_kwargs(kwargs, column)

        if "allow_none" not in kwargs:
            kwargs["allow_none"] = not kwargs["required"]

    def fields_for_model(self, *args, **kwargs):
        kwargs["include_fk"] = True
        return super().fields_for_model(*args, **kwargs)

    def property2field(self, prop, *args, **kwargs):
        if hasattr(prop, "columns"):
            column = prop.columns[0]
            if not hasattr(column, "info"):
                info = prop.info
            else:
                info = column.info
                prop.info = info

        field = super().property2field(prop, *args, **kwargs)

        is_relationship, foreign_key, target_model = get_foreign_key_column(prop)

        def flag_foreign_key(
            field,
            foreign_key,
            is_relationship,
            target_model,
            embedded=True,
            schema_class=None,
        ):
            field.foreign_key = foreign_key
            field.is_relationship = is_relationship
            field.target_model = target_model
            field.embedded = embedded
            field._schema_class = schema_class

        info = prop.info

        embedded = info.get("embedded", True)
        schema_class = info.get("schema_class", None)
        flag_foreign_key(
            field, foreign_key, is_relationship, target_model, embedded, schema_class
        )

        if isinstance(field, List):
            flag_foreign_key(
                field.container,
                foreign_key,
                is_relationship,
                target_model,
                embedded,
                schema_class,
            )

        description = info.get("description")
        if description is not None:
            field.metadata["description"] = description

        required = info.get("required")

        if required is not None:
            field.required = True
            field.allow_none = False

        return field

    def _get_field_class_for_property(self, prop):
        info = getattr(prop, "info", dict())

        field_class = info.get("marshmallow", dict()).get("field_class")

        if field_class is not None:
            return field_class

        direction = getattr(prop, "direction", None)

        if direction is not None and direction.name in (
            "ONETOMANY",
            "MANYTOONE",
            "MANYTOMANY",
        ):
            return UUID

        return super()._get_field_class_for_property(prop)


class ModelSchemaOpts(BaseModelSchemaOpts):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_converter = ModelConverter


def get_enum_value(enum):
    if isinstance(enum, str):
        return enum

    return enum.value


def check_roles(field, role=None):
    roles = field.metadata.get("roles")

    # A field that does not have a `roles` mapping
    # is always considered as read_only.
    field.dump_only = True

    if roles is not None:
        method = request.method.lower()

        if role is None:
            role = g.user.role

        # The user is allowed to read the field value
        readable = role and get_enum_value(role) in roles.get("get", tuple())

        # The user is allowed to write the field value
        writable = role and get_enum_value(role) in roles.get(method, tuple())

        if method == "get":
            writable = False

        if not readable and not writable:
            return

        if not readable:
            field.load_only = True

        if writable:
            field.dump_only = False

    return field


class ModelSchema(BaseModelSchema):
    TYPE_MAPPING = model_type_mapping
    OPTIONS_CLASS = ModelSchemaOpts

    def __init__(self, *args, **kwargs):
        effective_role = kwargs.pop("effective_role", None)
        super().__init__(*args, **kwargs)
        self.load_roles(role=effective_role)

    def load_roles(self, role=None):
        for key, field in self.fields.copy().items():
            field = check_roles(field, role)

            if field is None:
                del self.fields[key]
                continue

            self.fields[key] = field

    @property
    def session(self):
        return db_session

    @post_load
    def make_instance(self, data):
        data = PrefixedProcessingMixin.process_prefixed(self, data)
        for field in self.fields.values():
            if isinstance(field, ForeignField):
                value = data.pop(field.name, None)

                if value is not None:
                    field.populate_object(self.instance, value)

        return super().make_instance(data)


ModelSchema._BaseSchema__set_field_attrs = __set_field_attrs


converter = ModelConverter(schema_cls=ModelSchema)