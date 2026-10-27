import calendar
from datetime import date, timedelta

from app.conf import RECURRENCE_MAX_OCCURRENCES
from app.models.calendar_model import RecurrenceIn

FREQ_LABEL = {"daily": "day", "weekly": "week", "monthly": "month"}


def _add_months(day: date, months: int) -> date:
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1

    # The 31st repeats on the last day of a shorter month rather than skipping it.
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


# Every date the rule produces, the first one included, capped so one request
# cannot write an unbounded number of rows.
def occurrences(first: date, rule: RecurrenceIn) -> list[date]:
    days: list[date] = []
    step = 0

    while len(days) < RECURRENCE_MAX_OCCURRENCES:
        if rule.freq == "daily":
            current = first + timedelta(days=step * rule.interval)
        elif rule.freq == "weekly":
            current = first + timedelta(weeks=step * rule.interval)
        else:
            current = _add_months(first, step * rule.interval)

        if current > rule.until:
            break

        days.append(current)
        step += 1

    return days


# Stored on each row as "weekly;1;2026-12-31" — short, and enough to show
# "Repeats every week until 31 Dec" without a second table.
def encode(rule: RecurrenceIn) -> str:
    return f"{rule.freq};{rule.interval};{rule.until.isoformat()}"
