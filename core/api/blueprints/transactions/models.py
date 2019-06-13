from core.models.base import db, IntegerPK
from core.models.all import User, Merchant
from core.schema import ModelSchema


class Transaction(IntegerPK):
    """
    Transaction models
    Attributes:
        id              Primary key
        descriptor      String describing the transaction, like the one you can found on
                        your bank account
        amount          Amount of the transaction
        user_id         User Foreign key
        merchant_id     Merchant Foreign Key
    """
    descriptor = db.Column(db.String(256), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    executed_at = db.Column(db.Date(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    user = db.relationship(User, lazy=True, backref="transactions")
    merchant_id = db.Column(db.Integer, db.ForeignKey(Merchant.id))
    merchant = db.relationship(Merchant, lazy=True, backref="transactions")


db.Index('user_index', Transaction.id, Transaction.user_id)
db.Index('merchant_index', Transaction.id, Transaction.merchant_id)


class TransactionSchema(ModelSchema):
    """
    Shema describing the serialization of the Transaction Model
    """

    class Meta:
        model = Transaction


Transaction.schema_class = TransactionSchema
