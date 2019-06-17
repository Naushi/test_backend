from flask import jsonify
from flask_restplus import Resource
from sqlalchemy import func
from datetime import date
from calendar import monthrange

from . import merchants_api,  merchants
from core.models.all import Transaction
from core.models.base import session


@merchants_api.route('/<merchant_id>', defaults={'page': 1})
@merchants_api.route('/<merchant_id>/<int:page>', methods=['GET'])
# @merchants_api.doc(params={'merchant_id': 'ID of the merchant'})
class MerchantResource(Resource):
    def get(self, merchant_id, page):
        transactions = session.query(Transaction)
        transactions = transactions.filter(Transaction.merchant_id == merchant_id)
        transactions = transactions.order_by(Transaction.executed_at).paginate(page=page, per_page=50).items
        transactions_schema = Transaction.schema_class()
        res = []
        if len(transactions) != 0:
            for transaction in transactions:
                res.append(transactions_schema.dump(transaction).data)
            return jsonify(res)
        else:
            return jsonify('No transactions found.')


@merchants_api.route('/<merchant_id>/average')
@merchants_api.route('/<merchant_id>/average/<int:year>/<int:month>')
class MerchantAverageResource(Resource):
    def get(self, merchant_id, year=None, month=None):
        if year is not None and month is not None:
            num_days = monthrange(year, month)[1]
            average = session.query(func.avg(Transaction.amount))
            average = average.filter(Transaction.merchant_id == merchant_id)
            average = average.filter(Transaction.executed_at.between(date(year, month, 1), date(year, month, num_days)))
            average = average.scalar()
        else:
            average = session.query(func.avg(Transaction.amount))
            average = average.filter(Transaction.merchant_id == merchant_id)
            average = average.scalar()
        return jsonify(average)
