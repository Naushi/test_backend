from sqlalchemy_utils import EmailType

from core.models.base import db, IntegerPK
from core.schema import ModelSchema


class User(IntegerPK):
    """
    User models
    Attributes:
        id              The primary key of model
        email           Email of user, must be unique
    """
    email = db.Column(
        EmailType,
        nullable=False,
    )


class UserSchema(ModelSchema):
    """
    Schema describing the serialization of the User Model
    """

    class Meta:
        model = User

        fields = (
            "id",
            "email",
            "cgu_acceptance",
        )


User.schema_class = UserSchema
