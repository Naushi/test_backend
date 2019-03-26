from core.models.base import db, IntegerPK


class Merchant(IntegerPK):
    """
    Merchant model
    Attributes:
        id      Primary key
        name    Name of the merchant can be use to match transaction and merchant
    """
    name = db.Column(db.String(256), nullable=False)
