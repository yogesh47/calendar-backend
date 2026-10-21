import uuid
from datetime import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text

from app.auth.passwords import hash_password
from app.auth.users import STUDENT, SUPER_ADMIN, TPO
from app.conf import DATABASE_URL, DEFAULT_ORG_ID
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


# The accounts that can sign in. They used to be a tuple in the source; seeding
# them here means `make db-up` still leaves a usable system, and `make db-drop`
# takes them away with everything else.
SEED_USERS = (
    ("Priya Sharma", "tpo@campus.test", TPO, "tpo@1234"),
    ("Arjun Mehta", "tpo2@campus.test", TPO, "tpo2@1234"),
    ("Meera Iyer", "admin@campus.test", SUPER_ADMIN, "admin@1234"),
    ("Rahul Verma", "student@campus.test", STUDENT, "student@1234"),
)


# No id is written here: the column generates its own, so every environment gets
# its own real uuids instead of the four made-up ones this seed used to carry.
# Email is what decides whether a seed user is already there.
def seed_users() -> str:
    with SessionLocal() as db:
        existing = {
            row.email.lower()
            for row in db.execute(select(models.CalendarUser)).scalars().all()
        }
        added = 0
        for name, email, role, password in SEED_USERS:
            if email.lower() in existing:
                continue
            db.add(
                models.CalendarUser(
                    org_id=uuid.UUID(DEFAULT_ORG_ID),
                    name=name,
                    email=email,
                    role=role,
                    password_hash=hash_password(password),
                    is_active=True,
                )
            )
            added += 1
        db.commit()

        return f"{added} user(s) created" if added else "users already present"


def tables_now() -> str:
    return ", ".join(sorted(models.CalendarSettings.metadata.tables))


if __name__ == "__main__":
    print(create_database())
    print(run_migrations())
    print("tables:", tables_now())
    print(seed_settings())
    print(seed_users())
