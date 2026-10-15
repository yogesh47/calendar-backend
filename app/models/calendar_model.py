from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

EVENT_TYPES = (
    "ppt",
    "company_visit",
    "online_assessment",
    "training",
    "orientation",
    "practice_test",
    "deadline",
    "other",
    "my_reminder",
)

TIMED_TYPES = ("ppt", "company_visit", "online_assessment", "training", "orientation", "practice_test", "other")

MODE_TYPES = ("ppt", "company_visit", "training", "orientation", "practice_test", "other")

AUDIENCE_TYPES = tuple(entry for entry in EVENT_TYPES if entry != "my_reminder")


class AudienceIn(BaseModel):
    opportunity_type: Literal["job", "internship", "general"]
    courses: list[str] = []
    batches: list[int] = []
    departments: list[str] = []


class LinkedJobIn(BaseModel):
    kind: Literal["campus", "external"]
    campus_job: str | None = None
    url: str | None = None
    title: str | None = None


class EventIn(BaseModel):
    event_type: str
    title: str = Field(min_length=1, max_length=120)
    company: str | None = None
    event_date: date
    start_time: time | None = None
    end_time: time | None = None
    mode: Literal["offline", "online"] | None = None
    venue: str | None = Field(default=None, max_length=200)
    online_platform: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    note: str | None = Field(default=None, max_length=500)
    audience: AudienceIn | None = None
    linked_job: LinkedJobIn | None = None

    @model_validator(mode="after")
    def check_by_type(self):
        if self.event_type not in EVENT_TYPES:
            raise ValueError("Unknown event type")

        if self.event_type in TIMED_TYPES:
            if not self.start_time or not self.end_time:
                raise ValueError("Start and end time are required for this event type")
            if self.end_time <= self.start_time:
                raise ValueError("End time must be after start time")

        if self.event_type in MODE_TYPES:
            if not self.mode:
                raise ValueError("Mode is required for this event type")
            if self.mode == "offline" and not (self.venue or "").strip():
                raise ValueError("Venue is required for an offline event")
            if self.mode == "online" and not (self.online_platform or "").strip():
                raise ValueError("Online platform is required for an online event")

        if self.event_type in AUDIENCE_TYPES:
            audience = self.audience
            if not audience or not audience.courses or not audience.batches or not audience.departments:
                raise ValueError("Course, batch and department are required")

        if self.linked_job and self.linked_job.kind == "external":
            if not (self.linked_job.url or "").startswith("https://"):
                raise ValueError("Enter a valid link starting with https://")
            if not (self.linked_job.title or "").strip():
                raise ValueError("Job title is required for a pasted link")

        return self


class CancelIn(BaseModel):
    reason: Literal["postponed", "company_withdrew", "created_by_mistake", "other"]
    note: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def check_note(self):
        if self.reason == "other" and not (self.note or "").strip():
            raise ValueError("A short explanation is required")

        return self


class AudienceCountIn(BaseModel):
    audience: AudienceIn


class AudienceCountOut(BaseModel):
    count: int


class EventOut(BaseModel):
    event_id: str
    event_type: str
    title: str
    company: str | None
    event_date: date
    start_time: str | None
    end_time: str | None
    mode: str | None
    venue: str | None
    online_platform: str | None
    description: str | None
    note: str | None
    status: str
    cancel_reason: str | None
    cancel_note: str | None
    cancelled_at: datetime | None
    created_by: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    notified_count: int
    audience: AudienceIn | None
    linked_job: LinkedJobIn | None
    is_owner: bool


class NotificationOut(BaseModel):
    notification_id: str
    event_id: str
    message: str
    created_at: datetime
    is_read: bool
