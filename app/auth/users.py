import secrets
from dataclasses import dataclass

from app.conf import DEFAULT_ORG_ID

TPO = "tpo"
STUDENT = "student"
SUPER_ADMIN = "super_admin"


@dataclass(frozen=True)
class HardcodedUser:
    user_id: str
    org_id: str
    name: str
    email: str
    role: str
    password: str


HARDCODED_USERS = (
    HardcodedUser(
        user_id="22222222-2222-2222-2222-222222222222",
        org_id=DEFAULT_ORG_ID,
        name="Priya Sharma",
        email="tpo@campus.test",
        role=TPO,
        password="tpo@1234",
    ),
    HardcodedUser(
        user_id="44444444-4444-4444-4444-444444444444",
        org_id=DEFAULT_ORG_ID,
        name="Arjun Mehta",
        email="tpo2@campus.test",
        role=TPO,
        password="tpo2@1234",
    ),
    HardcodedUser(
        user_id="55555555-5555-5555-5555-555555555555",
        org_id=DEFAULT_ORG_ID,
        name="Meera Iyer",
        email="admin@campus.test",
        role=SUPER_ADMIN,
        password="admin@1234",
    ),
    HardcodedUser(
        user_id="33333333-3333-3333-3333-333333333333",
        org_id=DEFAULT_ORG_ID,
        name="Rahul Verma",
        email="student@campus.test",
        role=STUDENT,
        password="student@1234",
    ),
)


def find_by_email(email: str) -> HardcodedUser | None:
    wanted = email.strip().lower()

    return next((user for user in HARDCODED_USERS if user.email == wanted), None)


def find_by_id(user_id: str) -> HardcodedUser | None:
    return next((user for user in HARDCODED_USERS if user.user_id == user_id), None)


def authenticate(email: str, password: str) -> HardcodedUser | None:
    user = find_by_email(email)
    if not user:
        return None
    if not secrets.compare_digest(user.password, password):
        return None

    return user
