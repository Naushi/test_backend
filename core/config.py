from os import environ


def _environ_bool(var, default="false"):
    return environ.get(var, default).lower() == "true"


SERVER_NAME = environ["SERVER_NAME"]

# Bypass origin check
CHECK_ORIGIN = _environ_bool("CHECK_ORIGIN", "true")

# Logger
LOG_LEVEL = environ.get("LOG_LEVEL", "DEBUG")

# Flask Config
PREFERRED_URL_SCHEME = "https"

PROPAGATE_EXCEPTIONS = True

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = environ["SQLALCHEMY_DATABASE_URI"]
SQLALCHEMY_TEST_DATABASE_URI = environ.get(
    "SQLALCHEMY_TEST_DATABASE_URI", f"{SQLALCHEMY_DATABASE_URI}_test"
)
SQLALCHEMY_ECHO = _environ_bool("SQLALCHEMY_ECHO")
