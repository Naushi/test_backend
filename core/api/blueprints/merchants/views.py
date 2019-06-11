from flask import jsonify
from . import merchants
from core.models.all import Transaction, Merchant
from core.models.base import session


@merchants.route('/<merchant_id>/', methods=['GET'])
def list_transactions(merchant_id):
    transactions = session.query(Transaction.id, Transaction.descriptor).filter(Transaction.user_id == merchant_id).order_by(Transaction.executed_at).paginate(page=1, per_page=10).items
    print(transactions)
    return jsonify(dict(transactions))
