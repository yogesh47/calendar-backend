from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.conf import DEFAULT_ORG_TIMEZONE

ORG_TIMEZONE = ZoneInfo(DEFAULT_ORG_TIMEZONE)


def to_utc(day: date, wall_clock: time | None) -> datetime | None:
    if not wall_clock:
        return None

    return datetime.combine(day, wall_clock, tzinfo=ORG_TIMEZONE).astimezone(timezone.utc)  # noqa: UP017 - datetime.UTC needs Python 3.11


def local_time(moment: datetime | None) -> str | None:
    if not moment:
        return None

    return moment.astimezone(ORG_TIMEZONE).strftime("%H:%M")


def local_date(moment: datetime | None) -> date | None:
    if not moment:
        return None

    return moment.astimezone(ORG_TIMEZONE).date()
