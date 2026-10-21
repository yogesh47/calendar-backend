import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.users import SignedInUser
from app.db.models import CalendarPushDevice
from app.models.calendar_model import DeviceIn, DeviceOut

LOGGER = logging.getLogger("calendar.push")


def device_out(row: CalendarPushDevice) -> DeviceOut:
    return DeviceOut(device_id=str(row.device_id), platform=row.platform, created_at=row.created_at)


# The mobile app registers its push token here; one token belongs to one user.
def register(db: Session, user: SignedInUser, payload: DeviceIn) -> DeviceOut:
    try:
        row = db.scalar(select(CalendarPushDevice).where(CalendarPushDevice.token == payload.token))

        if row:
            row.user_id = uuid.UUID(user.user_id)
            row.org_id = uuid.UUID(user.org_id)
            row.platform = payload.platform
        else:
            row = CalendarPushDevice(
                org_id=uuid.UUID(user.org_id),
                user_id=uuid.UUID(user.user_id),
                token=payload.token,
                platform=payload.platform,
            )
            db.add(row)

        db.commit()
        db.refresh(row)

        return device_out(row)
    except Exception as err:
        LOGGER.error("register failed: %s", err)
        db.rollback()
        raise


def forget(db: Session, user: SignedInUser, token: str) -> None:
    try:
        db.query(CalendarPushDevice).filter(
            CalendarPushDevice.token == token,
            CalendarPushDevice.user_id == uuid.UUID(user.user_id),
        ).delete()
        db.commit()
    except Exception as err:
        LOGGER.error("forget failed: %s", err)
        db.rollback()
        raise


def devices_for(db: Session, user_id: str) -> list[CalendarPushDevice]:
    return list(
        db.scalars(select(CalendarPushDevice).where(CalendarPushDevice.user_id == uuid.UUID(user_id)))
    )
