import logging
import pytest

from flask.json import dumps
from flask.testing import FlaskClient
from core.config import SQLALCHEMY_TEST_DATABASE_URI

from core.api.app import create_app
from core.models.base import session as db_session
from core.models.migrations.utils import drop, migrate
from core.tests.fixtures import *  # noqa


class Client(FlaskClient):
    def open(self, *args, content_type="application/json", json=None, **kwargs):
        """
        Handle Authorization for given `user`.
        """
        headers = kwargs.pop("headers", {})

        headers["Accept"] = "application/json"

        headers.setdefault("Host", "domain.tld")

        if json is not None:
            headers["Content-Type"] = "application/json"
            kwargs.update(dict(data=dumps(json)))

        return super().open(*args, headers=headers, **kwargs)


@pytest.fixture(scope="session", autouse=True)
def app(request, tmp_media_dir):
    """
    Create assets required by the test suites and expose the current
    application.
    """
    # Initialize the application
    app = create_app(
        dict(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=SQLALCHEMY_TEST_DATABASE_URI,
            MEDIA_PATH=tmp_media_dir,
            SERVER_NAME="domain.tld",
        )
    )
    app.test_client_class = Client
    context = app.app_context()
    context.push()

    # Drop existing schema
    drop()

    # Create the database schema
    migrate(db_session.connection(), "head")

    db_session.commit()

    yield app

    context.pop()


@pytest.fixture(scope="function")
def client(app):
    """
    Expose test client.
    """
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def session(request, app):
    """
    Wraps each test within a database transaction and expose the current
    database session.
    Note: this depends on the `app` fixture because the flask_sqlalchemy
    database session requires a Flask app to be setup.
    """
    transaction = db_session.begin_nested()

    def commit():
        """Simulate a non-nested commit."""
        assert transaction.nested

        transaction.nested = False
        db_session.flush()
        transaction.nested = True

    transaction.commit = commit
    try:
        yield db_session
    finally:
        if transaction.is_active:
            transaction.rollback()

        db_session.rollback()

        db_session.expire_all()


def pytest_runtest_call(item):
    """
    Automatically flush the DB session before each test (but after fixtures)
    See: https://docs.pytest.org/en/latest/reference.html#hook-reference
    """
    db_session.flush()


@pytest.fixture(autouse=True)
def set_logging_level(caplog):
    caplog.set_level(logging.WARNING, logger="passlib")


@pytest.fixture(scope="function")
def mail(app):
    return app.extensions["mail"]
