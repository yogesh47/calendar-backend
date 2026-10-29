"""
The calendar as an iCalendar (.ics) feed.

Google Calendar and Outlook subscribe to a URL like this and
re-read it on their own schedule, so the student's own calendar follows the
campus one without an OAuth integration. It is read-only by design: changes are
made here and flow out.
"""

import re
from datetime import datetime, timedelta, timezone

from app.models.calendar_model import EventOut

TAGS = re.compile(r"<[^>]+>")


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _plain(html: str | None) -> str:
    text = TAGS.sub(" ", (html or "").replace("</p>", "\n").replace("<br>", "\n"))

    return re.sub(r"[ \t]+", " ", text).strip()


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: UP017


# RFC 5545 caps a line at 75 octets; longer ones continue on a line starting with a space.
def _fold(line: str) -> str:
    raw = line.encode()
    if len(raw) <= 75:
        return line

    parts, current = [], b""
    for char in line:
        encoded = char.encode()
        if len(current) + len(encoded) > (75 if not parts else 74):
            parts.append(current.decode())
            current = b""
        current += encoded
    parts.append(current.decode())

    return "\r\n ".join(parts)


def _event(item: EventOut, stamp: str) -> list[str]:
    lines = ["BEGIN:VEVENT", f"UID:{item.event_id}@campus-calendar", f"DTSTAMP:{stamp}"]

    if item.starts_at:
        lines.append(f"DTSTART:{_utc(item.starts_at)}")
        lines.append(f"DTEND:{_utc(item.ends_at or item.starts_at)}")
    else:
        lines.append(f"DTSTART;VALUE=DATE:{item.event_date:%Y%m%d}")
        lines.append(f"DTEND;VALUE=DATE:{item.event_date + timedelta(days=1):%Y%m%d}")

    # Google and Outlook show a subscribed event marked CANCELLED like any other, so the title says it too.
    title = f"Cancelled: {item.title}" if item.status == "cancelled" else item.title
    lines.append(f"SUMMARY:{_escape(title)}")

    where = item.venue if item.mode == "offline" else item.online_platform
    if where:
        lines.append(f"LOCATION:{_escape(where)}")

    details = _plain(item.description or item.note)
    if item.company:
        details = f"{item.company}\n{details}".strip()
    if details:
        lines.append(f"DESCRIPTION:{_escape(details)}")

    lines.append(f"STATUS:{'CANCELLED' if item.status == 'cancelled' else 'CONFIRMED'}")
    lines.append(f"LAST-MODIFIED:{item.updated_at.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}")  # noqa: UP017
    lines.append("END:VEVENT")

    return lines


def _wanted(item: EventOut, kinds: set[str]) -> bool:
    if item.event_type == "my_reminder":
        return "reminders" in kinds
    if item.event_type == "deadline":
        return "deadlines" in kinds
    return "events" in kinds


def build(
    items: list[EventOut],
    name: str,
    show_cancelled: bool = True,
    kinds: set[str] = frozenset({"events", "deadlines", "reminders"}),
) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: UP017
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//7Seers//Campus Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]

    for item in items:
        # Nudges are alerts about other items, and an event that no longer
        # applies to the student should drop out of their calendar too.
        if item.event_type == "nudge" or not item.applies_to_me or not _wanted(item, kinds):
            continue
        # "Created by mistake" is withdrawn for everyone, not just cancelled.
        if item.status == "cancelled" and (item.cancel_reason == "created_by_mistake" or not show_cancelled):
            continue
        lines.extend(_event(item, stamp))

    lines.append("END:VCALENDAR")

    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
