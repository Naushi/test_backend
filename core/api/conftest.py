import logging

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

    from core.models.all import Merchant, session
    from core.models.all import db as _db
    from data.merchant_name import merchant_names
    for name in merchant_names:
        Merchant(name=name).save()
    session.commit()

    engine = _db.engine
    insert_user = (
        f"""insert into "user" (email) select
                 concat('user', generate_series(1, 1000), '@test.com');"""
    )
    engine.execute(
        insert_user
    )
    session.commit()

    insert_transaction = (
        f"""
                insert into transaction(amount, descriptor, user_id, executed_at)
                select amount, descriptor, user_id, executed_at from (
                    select
                        generate_series(1, 10000),
                        (random() * 100)::decimal(6, 2) as 
                            amount,
                        'TUI' as 
                            descriptor, 
                        1 as 
                            user_id,
                        NOW() - '1 year'::INTERVAL * ROUND(RANDOM() * 100) as
                            executed_at
                ) as data;
                """
    )
    engine.execute(
        insert_transaction
    )
    session.commit()

    update_transaction = (
        """
        update transaction
            set merchant_id = merchant.id
            from merchant
                where transaction.descriptor = merchant.name;
        """
    )
    engine.execute(
        update_transaction
    )
    session.commit()

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
