import logging

from http import HTTPStatus

from flask import abort, jsonify
from flask import Request as BaseRequest


from werkzeug.exceptions import HTTPException, default_exceptions, InternalServerError


logger = logging.getLogger(__name__)


def error(exc):
    if not isinstance(exc, HTTPException):
        exc = InternalServerError()

    status = exc.code
    description = exc.description

    logger.info(f"Handling error {status}: {description}")

    return jsonify(dict(error=dict(description=description))), status


def init_error_handlers(app):
    for exception in default_exceptions.values():
        logger.debug(f"Registering handler for {exception}")
        app.register_error_handler(exception, error)

    if not app.config.get("TESTING", False):
        app.register_error_handler(Exception, error)


class Request(BaseRequest):
    def on_json_loading_failed(self, e):
        """
        Properly notify bad json formating.
        """
        abort(HTTPStatus.BAD_REQUEST, f"Invalid JSON: {e}")  # 400

    @property
    def remote_addr(self):
        forwarded_for = self.headers.get("X-Forwarded-For")

        if forwarded_for is not None:
            return forwarded_for.split(",")[0]

        return super().remote_addr
