from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.auth.tokens import issue_token
from app.auth.users import SignedInUser, authenticate
from app.db.session import get_db
from app.exceptions import AuthenticationError
from app.models.request_model import LoginRequest
from app.models.response_model import LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def to_response(user: SignedInUser) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        org_id=user.org_id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@router.post("/login")
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    user = authenticate(db, payload.email, payload.password)
    if not user:
        raise AuthenticationError("Email or password is incorrect")

    token, expires_in = issue_token(user)

    return LoginResponse(access_token=token, expires_in=expires_in, user=to_response(user))


@router.get("/me")
def me(user: Annotated[SignedInUser, Depends(current_user)]) -> UserResponse:
    return to_response(user)
