from datetime import datetime, timedelta, timezone

import jwt

from app.auth.users import SignedInUser
from app.conf import JWT_ALGORITHM, JWT_EXPIRY_MINUTES, JWT_SECRET


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


def read_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
