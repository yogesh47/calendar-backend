# Step 2 — Database

## Faisla: Docker me apna Postgres

Machine par Postgres pehle se chal raha tha (`:5432`), par usme `billion` naam
ka role hi nahi tha — DB banane ke liye `sudo -u postgres` chahiye hota. Uske
bajaye is project ka apna container uthaya:

| | |
|---|---|
| Kyun container | `sudo` nahi lagta, aur system ka Postgres chhua nahi jaata |
| Port | **5440** — 5432 aur 5433 dono pehle se busy the |
| Image | `postgres:16-alpine` (machine par pehle se thi) |

## Command

```bash
docker run -d --name campus-calendar-db \
  -e POSTGRES_USER=calendar \
  -e POSTGRES_PASSWORD=calendar \
  -e POSTGRES_DB=campus_calendar \
  -p 5440:5432 \
  postgres:16-alpine
```

DB (`campus_calendar`), user (`calendar`) aur password — teeno container start
hote hi ban jaate hain. Alag se `CREATE DATABASE` nahi chalana padta.

## Chal raha hai ya nahi

```bash
docker exec campus-calendar-db pg_isready -U calendar
docker exec campus-calendar-db psql -U calendar -d campus_calendar -c "select current_database(), current_user;"
```

```
 current_database | current_user
------------------+--------------
 campus_calendar  | calendar
```

## Connection string

`.env` me:

```
DATABASE_URL=postgresql+psycopg2://calendar:calendar@localhost:5440/campus_calendar
```

`psycopg2` **sync** driver hai — design doc §13 me yahi likha hai, to SQLAlchemy
bhi sync hi chalti hai (`async` nahi).

## Connection code — `app/db/session.py`

```python
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`pool_pre_ping=True` isliye ki container restart hone par mari hui connection
chupchaap use na ho jaye.

Route me aise milti hai:

```python
def health(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
```

## Roz ke commands

| Kaam | Command |
|---|---|
| Container chalu | `docker start campus-calendar-db` |
| Band | `docker stop campus-calendar-db` |
| psql kholo | `docker exec -it campus-calendar-db psql -U calendar -d campus_calendar` |
| Logs | `docker logs campus-calendar-db --tail 20` |
| **Poora uda do** | `docker rm -f campus-calendar-db` (data bhi jaayega) |

> Data container ke andar hai, volume me nahi. POC ke liye theek hai. Data bachana
> ho to `-v campus_calendar_data:/var/lib/postgresql/data` laga kar banao.
