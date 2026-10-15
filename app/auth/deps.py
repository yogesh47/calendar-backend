from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.tokens import read_token
from app.auth.users import HardcodedUser, find_by_id

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> HardcodedUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue")

    claims = read_token(credentials.credentials)
    if not claims:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired")

    user = find_by_id(str(claims.get("sub", "")))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired")

    return user


def require_role(*roles: str):
    def guard(user: HardcodedUser = Depends(current_user)) -> HardcodedUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this")

        return user

    return guard
