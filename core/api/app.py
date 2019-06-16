from flask import jsonify, request, Flask
from flask_uuid import FlaskUUID
from flask_restplus import Api

from core.json import JSONEncoder
from core.io import Request
from core.cli import init_cli
from core.models.base import db, session

from core.api.blueprints.merchants import merchants
from core.api.blueprints.user import users


def register_blueprints(app):
    app.register_blueprint(merchants, url_prefix='/merchants')
    app.register_blueprint(users, url_prefix='/users')


def bootstrap_app(app):
    app.json_encoder = JSONEncoder
    app.config["RESTFUL_JSON"] = {"cls": app.json_encoder}

    FlaskUUID(app)


def create_app(config=None, **kwargs):
    api = Api()
    app = Flask(__name__, static_folder=None, **kwargs)
    app.request_class = Request
    app.url_map.strict_slashes = False

    app.config.from_pyfile("../config.py")

    if config:
        app.config.update(config)
    db.init_app(app)

    register_blueprints(app)
    # Health check
    app.health_check_path = "/health-check"

    @app.before_request
    def health_check():
        if request.path == app.health_check_path:
            return jsonify(dict(status="healthy"))

    @app.after_request
    def headers(response):
        response.headers["Server"] = "Test API"
        response.headers["Keep-Alive"] = "timeout=5, max=100"
        return response

    @app.after_request
    def commit_db_session(response):
        session.commit()
        return response

    bootstrap_app(app)
    init_cli(app)

    print(app.url_map)
    api.init_app(app)
    return app
