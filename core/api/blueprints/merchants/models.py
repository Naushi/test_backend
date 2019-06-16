from core.models.base import db, IntegerPK
from core.schema import ModelSchema


class Merchant(IntegerPK):
    """
    Merchant model
    Attributes:
        id      Primary key
        name    Name of the merchant can be use to match transaction and merchant
    """
    name = db.Column(db.String(256), nullable=False)


class MerchantSchema(ModelSchema):
    class Meta:
        model = Merchant


Merchant.schema_class = MerchantSchema
