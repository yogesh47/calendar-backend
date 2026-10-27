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


# Only images this service stored itself; an event never points at an outside URL.
IMAGE_PATH = r"^/calendar/images/[0-9a-f]{32}\.(png|jpg|webp|gif)$"


class RecurrenceIn(BaseModel):
    freq: Literal["daily", "weekly", "monthly"]
    interval: int = Field(default=1, ge=1, le=12)
    until: date


class EventIn(BaseModel):
    event_type: str
    title: str = Field(min_length=1, max_length=120)
    company: str | None = None
    event_date: date
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    mode: Literal["offline", "online"] | None = None
    venue: str | None = Field(default=None, max_length=200)
    online_platform: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    note: str | None = Field(default=None, max_length=500)
    audience: AudienceIn | None = None
    linked_job: LinkedJobIn | None = None
    remind_before: Literal["none", "at_time", "15_min", "1_hour", "1_day"] | None = None
    linked_type: Literal["event", "job_deadline"] | None = None
    linked_id: str | None = None
    change_summary: str | None = Field(default=None, max_length=300)
    change_reason: str | None = Field(default=None, max_length=200)
    notify_on_change: bool = True
    recurrence: RecurrenceIn | None = None
    image_url: str | None = Field(default=None, pattern=IMAGE_PATH)

    @model_validator(mode="after")
    def check_by_type(self):
        if self.event_type not in EVENT_TYPES:
            raise ValueError("Unknown event type")

        if self.event_type in TIMED_TYPES:
            if not self.start_time or not self.end_time:
                raise ValueError("Start and end time are required for this event type")
            end_day = self.end_date or self.event_date
            if datetime.combine(end_day, self.end_time) <= datetime.combine(self.event_date, self.start_time):
                raise ValueError("End must be after the start")

        if self.event_type in MODE_TYPES:
            if not self.mode:
                raise ValueError("Mode is required for this event type")
            if self.mode == "offline" and not (self.venue or "").strip():
                raise ValueError("Venue is required for an offline event")
            if self.mode == "online" and not (self.online_platform or "").strip():
                raise ValueError("Online platform is required for an online event")

        # The audience is chosen after the event is published, so an event may
        # arrive without one. When it does come, it has to be complete.
        if self.audience and self.event_type in AUDIENCE_TYPES:
            audience = self.audience
            if not audience.courses or not audience.batches or not audience.departments:
                raise ValueError("Course, batch and department are required")

        if self.recurrence:
            if self.event_type == "my_reminder":
                raise ValueError("A reminder cannot repeat")
            if self.recurrence.until < self.event_date:
                raise ValueError("Repeat until cannot be before the start date")
            if (self.recurrence.until - self.event_date).days > 366:
                raise ValueError("An event can repeat for at most one year")

        if self.linked_job and self.linked_job.kind == "external":
            if not (self.linked_job.url or "").startswith("https://"):
                raise ValueError("Enter a valid link starting with https://")
            if not (self.linked_job.title or "").strip():
                raise ValueError("Job title is required for a pasted link")

        return self


class CancelIn(BaseModel):
    reason: Literal["postponed", "company_withdrew", "created_by_mistake", "other"]
    note: str | None = Field(default=None, max_length=200)
    # "series" cancels this occurrence and every later one of the same series.
    scope: Literal["one", "series"] = "one"

    @model_validator(mode="after")
    def check_note(self):
        if self.reason == "other" and not (self.note or "").strip():
            raise ValueError("A short explanation is required")

        return self


class DeleteManyIn(BaseModel):
    event_ids: list[str] = Field(default_factory=list, max_length=200)


class DeleteOut(BaseModel):
    deleted: list[str] = []
    skipped: list[str] = []
    count: int = 0


class AudienceCountIn(BaseModel):
    audience: AudienceIn


class AudienceCountOut(BaseModel):
    count: int


class AudienceSetIn(BaseModel):
    audience: AudienceIn


class ImageIn(BaseModel):
    # A data URL ("data:image/png;base64,...") — keeps uploads to plain JSON.
    data_url: str = Field(min_length=32, max_length=3_000_000)


class ImageOut(BaseModel):
    image_url: str


class FeedLinkOut(BaseModel):
    url: str


class EventOut(BaseModel):
    event_id: str
    event_type: str
    title: str
    company: str | None
    event_date: date
    end_date: date | None
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
    remind_before: str | None = None
    linked_type: str | None = None
    linked_id: str | None = None
    is_owner: bool
    applies_to_me: bool = True
    removed_reason: str | None = None
    change_summary: str | None = None
    change_reason: str | None = None
    deadline_counts: dict[str, int] | None = None
    series_id: str | None = None
    recurrence: str | None = None
    image_url: str | None = None


class ApplicationOut(BaseModel):
    application_id: str
    job_id: str
    application_status: str


class DeviceIn(BaseModel):
    token: str = Field(min_length=8, max_length=255)
    platform: Literal["android", "ios", "web"]


class DeviceOut(BaseModel):
    device_id: str
    platform: str
    created_at: datetime


class UnreadOut(BaseModel):
    unread: int


class NotificationOut(BaseModel):
    notification_id: str
    event_id: str
    message: str
    created_at: datetime
    is_read: bool
    kind: str = "new_event"
