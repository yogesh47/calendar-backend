from datetime import time

from pydantic import BaseModel, Field, model_validator


class SettingsIn(BaseModel):
    event_reminder_days_before: int = Field(ge=1, le=30)
    event_reminder_hours_before: int = Field(ge=1, le=12)
    deadline_reminder_days_before: int = Field(ge=1, le=30)
    deadline_reminder_same_day: bool
    daily_nudge_limit: int = Field(ge=1, le=10)
    quiet_hours_start: time
    quiet_hours_end: time

    @model_validator(mode="after")
    def check_quiet_hours(self):
        if self.quiet_hours_start == self.quiet_hours_end:
            raise ValueError("Quiet hours must start and end at different times")

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
