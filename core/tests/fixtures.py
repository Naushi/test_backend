# register here your different fixtures for testing
import pytest


@pytest.fixture(scope='session')
def tmp_media_dir():
    return '/tmp'
