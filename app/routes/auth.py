import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.auth.tokens import issue_token
from app.auth.users import SUPER_ADMIN, TPO, SignedInUser, authenticate
from app.db.models import CalendarUser
from app.db.session import get_db
from app.exceptions import AuthenticationError, InvalidInputError
from app.models.request_model import LoginRequest, TimeZoneIn
from app.models.response_model import LoginResponse, UserResponse
from app.services import nudges
from app.services.clock import is_zone
from app.services.ids import as_uuid
from app.services.settings_service import detect_org_zone, org_zone

LOGGER = logging.getLogger("calendar.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


def to_response(db: Session, user: SignedInUser) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        org_id=user.org_id,
        name=user.name,
        email=user.email,
        role=user.role,
        time_zone=user.time_zone,
        org_time_zone=org_zone(db, user.org_id),
    )


@router.post("/login")
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    user = authenticate(db, payload.email, payload.password)
    if not user:
        raise AuthenticationError("Email or password is incorrect")

    token, expires_in = issue_token(user)

    return LoginResponse(access_token=token, expires_in=expires_in, user=to_response(db, user))


@router.get("/me")
def me(user: Annotated[SignedInUser, Depends(current_user)], db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    return to_response(db, user)


# The browser says where the user is; their nudges and messages then read in that zone.
@router.put("/me/time-zone")
def set_time_zone(
    payload: TimeZoneIn,
    user: Annotated[SignedInUser, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    if not is_zone(payload.time_zone):
        raise InvalidInputError("That is not a time zone")

    row = db.get(CalendarUser, as_uuid(user.user_id))
    if row and row.time_zone != payload.time_zone:
        # Whoever signs in now is where the account is now: a login handed to
        # someone abroad gets their nudges on that person's clock from here on.
        old_zone = row.time_zone or org_zone(db, user.org_id)
        row.time_zone = payload.time_zone
        db.commit()
        try:
            nudges.move_to_zone(db, user.user_id, old_zone, payload.time_zone)
        except SQLAlchemyError:
            # The zone is saved either way; the nudges are re-timed when next scheduled.
            db.rollback()
            LOGGER.exception("could not move nudges to %s", payload.time_zone)

    # Staff signing in for the first time also tells the org where its campus is.
    if user.role in (TPO, SUPER_ADMIN):
        replaced = detect_org_zone(db, user.org_id, payload.time_zone)
        if replaced:
            try:
                nudges.move_org_to_zone(db, user.org_id, replaced, payload.time_zone)
            except SQLAlchemyError:
                db.rollback()
                LOGGER.exception("could not move the org's nudges to %s", payload.time_zone)

    return to_response(db, SignedInUser(**{**user.__dict__, "time_zone": payload.time_zone}))
