from datetime import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text

from app.conf import DATABASE_URL
from app.db import models
from app.db.session import SessionLocal

ROOT = Path(__file__).resolve().parents[1]


# The database itself is created here too, so one command is enough after a drop.
def create_database() -> str:
    parts = urlsplit(DATABASE_URL)
    name = parts.path.lstrip("/")
    admin_url = urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)

    with engine.connect() as connection:
        exists = connection.execute(
            text("select 1 from pg_database where datname = :name"), {"name": name}
        ).scalar()
        if not exists:
            connection.execute(text(f'create database "{name}"'))

    engine.dispose()

    return f"database already there: {name}" if exists else f"database created: {name}"


# Alembic runs every migration in order, so a fresh database ends up exactly like
# the running one — and an older database only gets what it is missing.
def run_migrations() -> str:
    config = Config(str(ROOT / "setup" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "setup" / "migrations"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(config, "head")

    return "schema is up to date"


# The platform runs on one settings row; create it the first time only.
def seed_settings() -> str:
    with SessionLocal() as db:
        if db.execute(select(models.CalendarSettings)).scalars().first():
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


def tables_now() -> str:
    return ", ".join(sorted(models.CalendarSettings.metadata.tables))


if __name__ == "__main__":
    print(create_database())
    print(run_migrations())
    print("tables:", tables_now())
    print(seed_settings())
