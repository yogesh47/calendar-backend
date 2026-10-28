from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.conf import DEFAULT_ORG_TIMEZONE

# Every conversion between a wall clock and an instant goes through here, and
# always names the zone it means. An org has its zone (its campus time — many
# orgs may share one), a user has theirs (where they are), and each event or
# reminder keeps the zone its times were typed in.

DEFAULT_ZONE = DEFAULT_ORG_TIMEZONE

# Kept for code that has no zone of its own to hand yet.
ORG_TIMEZONE = ZoneInfo(DEFAULT_ZONE)


# Old names browsers still report for the same zones. Chrome says
# "Asia/Calcutta" in India; everything here stores the current name, so two
# people in one city never end up with two different zones.
ZONE_ALIASES = {
    "Asia/Calcutta": "Asia/Kolkata",
    "Asia/Katmandu": "Asia/Kathmandu",
    "Asia/Rangoon": "Asia/Yangon",
    "Asia/Saigon": "Asia/Ho_Chi_Minh",
    "Asia/Dacca": "Asia/Dhaka",
    "Asia/Thimbu": "Asia/Thimphu",
    "Asia/Ulan_Bator": "Asia/Ulaanbaatar",
    "Europe/Kiev": "Europe/Kyiv",
    "Europe/Uzhgorod": "Europe/Kyiv",
    "Europe/Zaporozhye": "Europe/Kyiv",
    "Atlantic/Faeroe": "Atlantic/Faroe",
    "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
    "America/Godthab": "America/Nuuk",
    "Pacific/Enderbury": "Pacific/Kanton",
    "Africa/Asmera": "Africa/Asmara",
    "Etc/UTC": "UTC",
}


def canonical_zone(name: str | None) -> str | None:
    """The current IANA name for a zone, e.g. "Asia/Calcutta" → "Asia/Kolkata"."""
    return ZONE_ALIASES.get(name, name) if name else name


def is_zone(name: str | None) -> bool:
    if not name:
        return False
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False

    return True


def zone_of(name: str | None) -> ZoneInfo:
    """The named zone, or the default when there is none or it is not a real zone."""
    return ZoneInfo(name) if is_zone(name) else ORG_TIMEZONE


def to_utc(day: date, wall_clock: time | None, zone: str | None = None) -> datetime | None:
    if not wall_clock:
        return None

    return datetime.combine(day, wall_clock, tzinfo=zone_of(zone)).astimezone(timezone.utc)  # noqa: UP017 - datetime.UTC needs Python 3.11


def local_time(moment: datetime | None, zone: str | None = None) -> str | None:
    if not moment:
        return None

    return moment.astimezone(zone_of(zone)).strftime("%H:%M")


def local_date(moment: datetime | None, zone: str | None = None) -> date | None:
    if not moment:
        return None

    return moment.astimezone(zone_of(zone)).date()


def in_zone(moment: datetime, zone: str | None = None) -> datetime:
    return moment.astimezone(zone_of(zone))


def zone_label(moment: datetime, zone: str | None = None) -> str:
    """The short name a person reads, e.g. "IST", "AEDT", "GMT"."""
    return moment.astimezone(zone_of(zone)).tzname() or (zone or DEFAULT_ZONE)
