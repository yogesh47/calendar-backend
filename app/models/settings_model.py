from datetime import time

from pydantic import BaseModel, Field, model_validator

from app.services.clock import canonical_zone, is_zone


class SettingsIn(BaseModel):
    event_reminder_days_before: int = Field(ge=1, le=30)
    event_reminder_hours_before: int = Field(ge=1, le=12)
    deadline_reminder_days_before: int = Field(ge=1, le=30)
    deadline_reminder_same_day: bool
    daily_nudge_limit: int = Field(ge=1, le=10)
    quiet_hours_start: time
    quiet_hours_end: time
    # The org's campus time, e.g. "Asia/Kolkata", "Australia/Sydney", "Europe/London".
    # Left out, the org keeps the zone it has.
    time_zone: str | None = None

    @model_validator(mode="after")
    def check_quiet_hours(self):
        if self.quiet_hours_start == self.quiet_hours_end:
            raise ValueError("Quiet hours must start and end at different times")
        self.time_zone = canonical_zone(self.time_zone)
        if self.time_zone is not None and not is_zone(self.time_zone):
            raise ValueError("Pick a real time zone, e.g. Asia/Kolkata")

        return self


class SettingsOut(BaseModel):
    event_reminder_days_before: int
    event_reminder_hours_before: int
    deadline_reminder_days_before: int
    deadline_reminder_same_day: bool
    daily_nudge_limit: int
    quiet_hours_start: str
    quiet_hours_end: str
    updated_at: str | None = None
    time_zone: str = "Asia/Kolkata"
