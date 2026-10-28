from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.users import SUPER_ADMIN, SignedInUser
from app.db.session import get_db
from app.models.settings_model import SettingsIn, SettingsOut
from app.services import nudges, settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


# Returns the signed-in admin's org settings: nudge timings, quiet hours and its time zone.
@router.get("")
def read_settings(
    user: Annotated[SignedInUser, Depends(require_role(SUPER_ADMIN))],
    db: Annotated[Session, Depends(get_db)],
) -> SettingsOut:
    return settings_service.read_settings(db, user.org_id)


# Saves new nudge timings, the daily limit and quiet hours; only a Super Admin may.
@router.put("")
def save_settings(
    payload: SettingsIn,
    user: Annotated[SignedInUser, Depends(require_role(SUPER_ADMIN))],
    db: Annotated[Session, Depends(get_db)],
) -> SettingsOut:
    old_zone = settings_service.org_zone(db, user.org_id)
    saved = settings_service.save_settings(db, user, payload)
    # Students with no zone of their own keep their 8 / 9 a.m. nudges on the new campus clock.
    if saved.time_zone != old_zone:
        nudges.move_org_to_zone(db, user.org_id, old_zone, saved.time_zone)

    return saved
