from flask import Blueprint
from flask_restplus import Api

users = Blueprint('users', __name__)

users_api = Api(users, default='Users', default_label='Routes relating to users')
