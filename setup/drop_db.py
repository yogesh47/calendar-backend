import sys
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, text

from app.conf import DATABASE_URL

WARNING = "This deletes the whole database. Run it with --yes to go ahead."


def split_url(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    name = parts.path.lstrip("/")
    admin = urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))

    return admin, name


# Postgres cannot drop a database that still has connections, so they go first.
def drop(admin_url: str, name: str) -> None:
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)

    with engine.connect() as connection:
        connection.execute(
            text(
                "select pg_terminate_backend(pid) from pg_stat_activity "
                "where datname = :name and pid <> pg_backend_pid()"
            ),
            {"name": name},
        )
        connection.execute(text(f'drop database if exists "{name}"'))

    engine.dispose()


def main() -> int:
    if "--yes" not in sys.argv:
        print(WARNING)
        return 1

    admin_url, name = split_url(DATABASE_URL)
    drop(admin_url, name)
    print(f"database deleted: {name}")
    print("wapas banane ke liye: make db-up")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
