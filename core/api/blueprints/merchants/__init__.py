from flask import Blueprint
from flask_restplus import Api

merchants = Blueprint('merchants', __name__)

merchants_api = Api(merchants, default='Merchants', default_label='Routes relating to merchants')
