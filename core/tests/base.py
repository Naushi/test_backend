import os
from contextlib import contextmanager

import arrow
from flask import g


def assert_datetime_equals(value, target):
    value = arrow.get(value).datetime.replace(microsecond=0)
    assert value == target.replace(microsecond=0)


@contextmanager
def mock_request_context(app, user, method="GET", url="/"):
    with app.test_request_context(url, method=method):
        g.user = user
        yield
        g.user = None


@contextmanager
def sample_file(filename):
    path = os.path.join(os.path.dirname(__file__), "media", filename)
    with open(path, "rb") as file_:
        yield file_


def assert_schema(class_, app, user, dump_only, writable=None, method="post"):
    if writable is None:
        writable = list()

    with mock_request_context(app, user, method=method.upper()):
        schema = class_.get_schema()

    fields = schema.fields

    all_ = writable + dump_only

    assert sorted(list(fields.keys())) == sorted(all_)

    for key, field in fields.items():
        assert (
            not field.dump_only
            and key not in dump_only
            or key in dump_only
            and field.dump_only
        )

    return schema
