import sys

from sqlalchemy import text

from app.conf import DATABASE_URL
from app.db.session import engine


def safe_url(url: str) -> str:
    if "@" not in url:
        return url
    head, tail = url.rsplit("@", 1)
    return f"{head.split('//')[0]}//***@{tail}"


def main() -> int:
    try:
        with engine.connect() as connection:
            database, user = connection.execute(
                text("select current_database(), current_user")
            ).one()
            tables = connection.execute(
                text(
                    "select count(*) from information_schema.tables "
                    "where table_schema = 'public'"
                )
            ).scalar_one()
    except Exception as error:
        print("DB CONNECTION FAILED")
        print(f"  url    : {safe_url(DATABASE_URL)}")
        print(f"  reason : {type(error).__name__}: {str(error).splitlines()[0]}")
        return 1

    print("DB CONNECTION SUCCESSFUL")
    print(f"  url    : {safe_url(DATABASE_URL)}")
    print(f"  db     : {database}")
    print(f"  user   : {user}")
    print(f"  tables : {tables}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
