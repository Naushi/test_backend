from datetime import date, datetime, timedelta

from arrow.parser import DateTimeParser, ParserError
from pytz import utc


_parser = DateTimeParser()


def parse_html5_date(value):
    return date(*value.split("-"))


def to_utc(dt):
    """
    Make sure a datetime uses the UTC timezone
    """
    if dt.tzinfo is None:
        return utc.localize(dt)

    return dt.astimezone(utc)


def utcnow():
    """
    Return the current date & time with explicit UTC timezone
    """
    return to_utc(datetime.utcnow())


def parse_iso_datetime(value, timezone=None):
    """
    Parse ISO 8601 datetime.
    """
    try:
        if len(value) < 10:
            raise ParserError()

        value = _parser.parse_iso(value)

        if timezone is not None:
            value = timezone.localize(value)

        if value.tzinfo is None:
            return to_utc(value)

        return value

    except ParserError as exc:
        raise ValueError("Invalid datetime format") from exc


def format_iso_datetime(datetime_):
    """
    Format datetime as ISO 8601
    We first convert the datetime to the UTC timezone
    and format it as ISO 8601 without microseconds.
    """
    return to_utc(datetime_).replace(microsecond=0).isoformat()


def get_utc_date(day_delta=None):
    day = utcnow().date()

    if day_delta is not None:
        day = day + timedelta(days=day_delta)

    day = datetime(day.year, day.month, day.day, tzinfo=utc)

    return day
