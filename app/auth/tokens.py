from datetime import datetime, timedelta, timezone

import jwt

from app.auth.users import SignedInUser
from app.conf import FEED_TOKEN_DAYS, JWT_ALGORITHM, JWT_EXPIRY_MINUTES, JWT_SECRET

FEED = "feed"


def issue_token(user: SignedInUser) -> tuple[str, int]:
    expires_in = JWT_EXPIRY_MINUTES * 60
    payload = {
        "sub": user.user_id,
        "org_id": user.org_id,
        "role": user.role,
        "email": user.email,
        "name": user.name,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES),  # noqa: UP017
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM), expires_in


def _decode(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# A session token only. A feed token carries `purpose` and is refused here, so a
# calendar URL pasted into Google can never be used to sign in.
def read_token(token: str) -> dict | None:
    claims = _decode(token)

    return claims if claims and "purpose" not in claims else None


# The token inside a calendar subscription URL. Calendar apps cannot send a
# header, so it rides in the URL and lives much longer than a session; all it
# can do is read that one user's .ics feed.
def issue_feed_token(user: SignedInUser) -> str:
    payload = {
        "sub": user.user_id,
        "purpose": FEED,
        "exp": datetime.now(timezone.utc) + timedelta(days=FEED_TOKEN_DAYS),  # noqa: UP017
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def read_feed_token(token: str) -> dict | None:
    claims = _decode(token)

    return claims if claims and claims.get("purpose") == FEED else None
