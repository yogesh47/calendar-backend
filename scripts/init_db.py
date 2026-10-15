from datetime import time

from sqlalchemy import select

from app.db import models
from app.db.session import Base, SessionLocal, engine


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_settings() -> str:
    with SessionLocal() as db:
        existing = db.execute(select(models.CalendarSettings)).scalars().first()
        if existing:
            return "settings row already present"

        db.add(
            models.CalendarSettings(
                event_reminder_days_before=1,
                event_reminder_hours_before=1,
                deadline_reminder_days_before=2,
                deadline_reminder_same_day=True,
                daily_nudge_limit=3,
                quiet_hours_start=time(22, 0),
                quiet_hours_end=time(7, 0),
            )
        )
        db.commit()

        return "settings row created"


if __name__ == "__main__":
    create_tables()
    print("tables ready:", ", ".join(sorted(Base.metadata.tables)))
    print(seed_settings())
