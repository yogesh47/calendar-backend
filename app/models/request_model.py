from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=200)
