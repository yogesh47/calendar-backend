from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.tokens import read_token
from app.auth.users import SignedInUser, find_by_id
from app.db.session import get_db
from app.exceptions import AuthenticationError, PermissionDeniedError

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> SignedInUser:
    """
    Who is calling, resolved against the database on every request.

    The token only says which id signed in; the row is what decides whether that
    account still exists, is still active and still holds the role it had when
    the token was handed out. A token outliving the account it names is the whole
    reason this reads the row instead of trusting the claims.
    """
    if credentials is None:
        raise AuthenticationError("Sign in to continue")

    claims = read_token(credentials.credentials)
    if not claims:
        raise AuthenticationError("Your session has expired")

    user = find_by_id(db, str(claims.get("sub", "")))
    if not user:
        raise AuthenticationError("Your session has expired")

    return user


def require_role(*roles: str):
    def guard(user: Annotated[SignedInUser, Depends(current_user)]) -> SignedInUser:
        if user.role not in roles:
            raise PermissionDeniedError("You do not have access to this")

        return user

    return guard
