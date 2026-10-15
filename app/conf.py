from os import environ

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://calendar:calendar@localhost:5440/campus_calendar",
)

JWT_SECRET = environ.get("JWT_SECRET", "change-me-in-every-environment")
JWT_ALGORITHM = environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = int(environ.get("JWT_EXPIRY_MINUTES", 720))

DEFAULT_ORG_TIMEZONE = environ.get("DEFAULT_ORG_TIMEZONE", "Asia/Kolkata")
DEFAULT_ORG_ID = environ.get("DEFAULT_ORG_ID", "11111111-1111-1111-1111-111111111111")

CALENDAR_MAX_RANGE_DAYS = int(environ.get("CALENDAR_MAX_RANGE_DAYS", 62))
STUDENT_REMINDER_LIMIT = int(environ.get("STUDENT_REMINDER_LIMIT", 50))
CAMPUS_CALENDAR_ENABLED = environ.get("CAMPUS_CALENDAR_ENABLED", "true").lower() == "true"

CORS_ORIGINS = [
    origin.strip()
    for origin in environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
