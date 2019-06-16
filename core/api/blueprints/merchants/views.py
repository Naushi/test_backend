from flask import jsonify
from flask_restplus import Resource
from . import merchants_api
from core.models.all import Transaction
from core.models.base import session


@merchants_api.route('/<merchant_id>', defaults={'page': 1})
@merchants_api.route('/<merchant_id>/<int:page>', methods=['GET'])
class UserResource(Resource):
    def get(self, merchant_id, page=1):
        transactions = session.query(Transaction).filter(Transaction.merchant_id == merchant_id).order_by(Transaction.executed_at).paginate(page=page, per_page=50).items
        transactions_schema = Transaction.schema_class()
        res = []
        if len(transactions) != 0:
            for transaction in transactions:
                res.append(transactions_schema.dump(transaction).data)
            return jsonify(res)
        else:
            return jsonify('No transactions found.')
