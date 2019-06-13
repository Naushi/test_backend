from flask import jsonify
from . import merchants
from core.models.all import Transaction
from core.models.base import session


@merchants.route('/<merchant_id>', defaults={'page': 1})
@merchants.route('/<merchant_id>/<int:page>', methods=['GET'])
def list_transactions(merchant_id, page=1):
    transactions = session.query(Transaction).filter(Transaction.merchant_id == merchant_id).order_by(Transaction.executed_at).paginate(page=page, per_page=50).items
    transactions_schema = Transaction.schema_class()
    res = []
    if len(transactions) != 0:
        for transaction in transactions:
            res.append(transactions_schema.dump(transaction).data)
        return jsonify(res)
    else:
        return jsonify('No transactions found.')
