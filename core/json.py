import datetime
import uuid
from enum import Enum

from flask.json import JSONEncoder as BaseJSONEncoder


class JSONEncoder(BaseJSONEncoder):
    def default(self, o):

        if isinstance(o, uuid.UUID):
            return str(o)

        if isinstance(o, datetime.datetime) or isinstance(o, datetime.date):
            return o.isoformat()

        if isinstance(o, Enum):
            return o.value

        return super().default(o)
