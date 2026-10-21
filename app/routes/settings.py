from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.users import SUPER_ADMIN, SignedInUser
from app.db.session import get_db
from app.models.settings_model import SettingsIn, SettingsOut
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


# Returns the one row of calendar and nudge settings the whole platform runs on.
@router.get("")
def read_settings(
    _: Annotated[SignedInUser, Depends(require_role(SUPER_ADMIN))],
    db: Annotated[Session, Depends(get_db)],
) -> SettingsOut:
    return settings_service.read_settings(db)


# Saves new nudge timings, the daily limit and quiet hours; only a Super Admin may.
@router.put("")
def save_settings(
    payload: SettingsIn,
    user: Annotated[SignedInUser, Depends(require_role(SUPER_ADMIN))],
    db: Annotated[Session, Depends(get_db)],
) -> SettingsOut:
    return settings_service.save_settings(db, user, payload)
