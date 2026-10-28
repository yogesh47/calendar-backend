from pydantic import BaseModel, Field, field_validator

from app.services.clock import canonical_zone

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


class TimeZoneIn(BaseModel):
    # An IANA name as the browser reports it, e.g. "America/New_York".
    time_zone: str = Field(min_length=1, max_length=64)

    @field_validator("time_zone")
    @classmethod
    def current_name(cls, value: str) -> str:
        return canonical_zone(value)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=200)
