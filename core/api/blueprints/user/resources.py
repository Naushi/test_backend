from flask import jsonify
from flask_restplus import Resource
from sqlalchemy import func
from datetime import date
from calendar import monthrange

from . import users_api, users
from core.models.all import Transaction
from core.models.base import session


@users_api.route('/<user_id>', defaults={'page': 1})
@users_api.route('/<user_id>/<int:page>', methods=['GET'])
# @users_api.doc(params={'user_id': 'ID of the user'})
class UserResource(Resource):
    def get(self, user_id, page):
        transactions = session.query(Transaction)
        transactions = transactions.filter(Transaction.user_id == user_id)
        transactions = transactions.order_by(Transaction.executed_at).paginate(page=page, per_page=50).items
        transactions_schema = Transaction.schema_class()
        res = []
        if len(transactions) != 0:
            for transaction in transactions:
                res.append(transactions_schema.dump(transaction).data)
            return jsonify(res)
        else:
            return jsonify('No transactions found.')


@users_api.route('/<user_id>/average')
@users_api.route('/<user_id>/average/<int:year>/<int:month>')
class UserAverageResource(Resource):
    def get(self, user_id, year=None, month=None):
        if year is not None and month is not None:
            num_days = monthrange(year, month)[1]
            average = session.query(func.avg(Transaction.amount))
            average = average.filter(Transaction.user_id == user_id)
            average = average.filter(Transaction.executed_at.between(date(year, month, 1), date(year, month, num_days)))
            average = average.scalar()
        else:
            average = session.query(func.avg(Transaction.amount))
            average = average.filter(Transaction.user_id == user_id)
            average = average.scalar()
        return jsonify(average)
