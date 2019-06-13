from flask import jsonify
from . import users
from core.models.all import Transaction
from core.models.base import session


@users.route('/<user_id>', defaults={'page': 1})
@users.route('/<user_id>/<int:page>', methods=['GET'])
def list_transactions(user_id, page=1):
    transactions = session.query(Transaction).filter(Transaction.user_id == user_id).order_by(Transaction.executed_at).paginate(page=page, per_page=50).items
    transactions_schema = Transaction.schema_class()
    res = []
    if len(transactions) != 0:
        for transaction in transactions:
            res.append(transactions_schema.dump(transaction).data)
        return jsonify(res)
    else:
        return jsonify('No transactions found.')
