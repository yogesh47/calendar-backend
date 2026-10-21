import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import ARRAY, UUID


# The id is generated on BOTH sides on purpose: `default` covers an ORM insert,
# `server_default` covers a plain `INSERT` written by hand or by a migration, so
# neither route has to remember to mint one. gen_random_uuid() is built into
# Postgres 13 and later — no extension needed.
def primary_key() -> Column:
    return Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sql_text("gen_random_uuid()"),
    )


def required_id(index: bool = False) -> Column:
    return Column(UUID(as_uuid=True), nullable=False, index=index)


def optional_id() -> Column:
    return Column(UUID(as_uuid=True), nullable=True)


def event_id(unique: bool = False, index: bool = False) -> Column:
    return Column(
        UUID(as_uuid=True),
        ForeignKey("calendar_event.event_id", ondelete="CASCADE"),
        nullable=False,
        unique=unique,
        index=index,
    )


def text(length: int, nullable: bool = True, default: str | None = None) -> Column:
    return Column(String(length), nullable=nullable, default=default)


def long_text() -> Column:
    return Column(Text, nullable=True)


def day(nullable: bool = False) -> Column:
    return Column(Date, nullable=nullable)


def clock(nullable: bool = True) -> Column:
    return Column(Time, nullable=nullable)


def moment(nullable: bool = True, index: bool = False) -> Column:
    return Column(DateTime(timezone=True), nullable=nullable, index=index)


def created_at() -> Column:
    return Column(DateTime(timezone=True), nullable=False, server_default=func.now())


def updated_at() -> Column:
    return Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


def flag(default: bool = False) -> Column:
    return Column(Boolean, nullable=False, default=default)


def count(default: int = 0) -> Column:
    return Column(Integer, nullable=False, default=default)


def text_list() -> Column:
    return Column(ARRAY(String), nullable=False)


def number_list() -> Column:
    return Column(ARRAY(Integer), nullable=False)
