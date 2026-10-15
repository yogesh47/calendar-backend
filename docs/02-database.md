# Step 2 — Database

## Faisla: Docker me apna Postgres

Machine par Postgres pehle se chal raha tha (`:5432`), par usme `billion` naam ka
role hi nahi tha — DB banane ke liye `sudo -u postgres` chahiye hota. Uske bajaye
is project ka apna container uthaya: `sudo` nahi lagta, aur system ka Postgres
chhua nahi jaata.

## Banane ka command

```bash
docker run -d --name campus-calendar-db \
  -e POSTGRES_USER=calendar \
  -e POSTGRES_PASSWORD=calendar \
  -e POSTGRES_DB=campus_calendar \
  -p 5440:5432 \
  postgres:16-alpine
```

Database, user aur password — teeno container start hote hi ban jaate hain.
Alag se `CREATE DATABASE` nahi chalana padta.

## Credentials

| Kya | Value | Kahan se aaya |
|---|---|---|
| Host | `localhost` | |
| **Port** | **`5440`** | `-p 5440:5432` — bahar 5440, andar 5432 |
| **Database** | **`campus_calendar`** | `POSTGRES_DB` |
| Username | `calendar` | `POSTGRES_USER` |
| Password | `calendar` | `POSTGRES_PASSWORD` |

5440 isliye ki 5432 aur 5433 dono pehle se busy the.

Ye POC ke credentials hain. Asli environment me password env se aana chahiye,
command me likha hua nahi.

## Terminal se connection check

Chaar sawaal, upar se neeche chalao — jahan ruke, wahi dikkat hai.

**1. Docker khud chal raha hai?**

```bash
docker info --format '{{.ServerVersion}}'
```

Version number aa gaya to Docker chalu hai. Ye aaye to nahi:

```
failed to connect to the docker API at unix:///var/run/docker.sock;
check if the path is correct and if the daemon is running
```

Is machine par Docker **snap** se chalta hai, isliye chalu/band isse dekho:

```bash
snap services docker
sudo snap start docker
```

```
Service          Startup  Current  Notes
docker.dockerd   enabled  active   -
```

> `systemctl is-active docker` yahan **`inactive`** bolta hai jabki Docker chal
> raha hota hai — wo `docker.service` dhoondhta hai, aur snap wala
> `snap.docker.dockerd` hai. Us jawab par mat jaana.

**2. Container chalu hai?**

```bash
docker ps --filter name=campus-calendar-db
```

`Up 20 minutes` aur `0.0.0.0:5440->5432/tcp` dikhna chahiye. Kuch na dikhe to
container band hai — `docker start campus-calendar-db`.

**3. Postgres jawab de raha hai?**

```bash
docker exec campus-calendar-db pg_isready -U calendar
```

```
/var/run/postgresql:5432 - accepting connections
```

**4. Connection ban rahi hai?** — ek command, seedha jawab

```bash
cd calendar-backend
source .venv/bin/activate
PYTHONPATH=. python scripts/check_db.py
```

Bani to:

```
DB CONNECTION SUCCESSFUL
  url    : postgresql+psycopg2://***@localhost:5440/campus_calendar
  db     : campus_calendar
  user   : calendar
  tables : 6
```

Nahi bani to:

```
DB CONNECTION FAILED
  url    : postgresql+psycopg2://***@localhost:5440/campus_calendar
  reason : OperationalError: connection to server at "localhost" (127.0.0.1), port 5440 failed: Connection refused
```

Script wahi `DATABASE_URL` padhti hai jo app padhta hai — to ye pass hua matlab
**app bhi jud jaayega**. Exit code bhi deta hai (`0` pass, `1` fail), to CI me
seedha laga sakte ho.

Password output me nahi aata, `***` ho jaata hai.

Sirf psql se dekhna ho to:

```bash
PGPASSWORD=calendar psql -h localhost -p 5440 -U calendar -d campus_calendar \
  -c "select current_database(), current_user;"
```

> `psql` ke andar `inet_server_port()` **5432** batata hai, 5440 nahi — wo
> container ke andar ka port hai. 5440 bahar ka hai. Dono theek hain.

### Jab connection na bane

| Error | Matlab | Ilaj |
|---|---|---|
| `Connection refused` | us port par koi sun hi nahi raha | container band hai — `docker start campus-calendar-db` |
| `role "billion" does not exist` | port chhoot gaya, machine ka doosra Postgres pakad liya | `-p 5440` lagao |
| `database "..." does not exist` | DB ka naam galat | `campus_calendar` |
| `password authentication failed` | user/password galat | dono `calendar` hain |
| `Cannot connect to the Docker daemon` | Docker hi band hai | upar step 1 |

### Aur kya dekh sakte ho

| Sawaal | Command |
|---|---|
| Tables bani hain? | `docker exec campus-calendar-db psql -U calendar -d campus_calendar -c "\dt"` |
| Settings ki row hai? | `docker exec campus-calendar-db psql -U calendar -d campus_calendar -c "select * from calendar_settings;"` |
| API ko DB mil raha hai? | `curl -s http://127.0.0.1:8001/health` → `{"status":"ok","database":"up"}` |
| Port kis par khula hai? | `ss -ltn \| grep 5440` |
| Kuch toota to logs | `docker logs campus-calendar-db --tail 20` |

## App kaise judta hai

`.env`:

```
DATABASE_URL=postgresql+psycopg2://calendar:calendar@localhost:5440/campus_calendar
```

`app/db/session.py`:

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

`psycopg2` sync driver hai (design doc, Libraries), to SQLAlchemy bhi sync chalti hai.
`pool_pre_ping=True` isliye ki container restart hone par mari hui connection
chupchaap use na ho jaye.

Route me:

```python
def health(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
```

## Data dekhna — psql se

```bash
docker exec -it campus-calendar-db psql -U calendar -d campus_calendar
```

| Command | Kya dikhata hai |
|---|---|
| `\dt` | saari tables |
| `\d calendar_event` | ek table ke columns, types, indexes |
| `select * from calendar_settings;` | settings ki ek row |
| `\q` | bahar |

Bina andar ghuse, ek line me:

```bash
docker exec campus-calendar-db psql -U calendar -d campus_calendar -c "\dt"
```

### Flags ka matlab

```
docker exec -it campus-calendar-db psql -U calendar -d campus_calendar -c "\dt"
       ────  ──  ─────────────────  ──── ──────────  ──────────────────  ──────
         1    2          3            4       5               6             7
```

| # | Tukda | Matlab |
|---|---|---|
| 1 | `exec` | chalu container ke **andar** ek command chalao |
| 2 | `-it` | **i**nteractive + **t**erminal — tab lagao jab andar baith kar type karna ho. Ek baar ka jawab chahiye to mat lagao |
| 3 | `campus-calendar-db` | kis container me |
| 4 | `psql` | Postgres ka command-line client |
| 5 | `-U calendar` | **U**ser — kis user se judna |
| 6 | `-d campus_calendar` | **d**atabase — kaunsa database |
| 7 | `-c "\dt"` | **c**ommand — ye chalao aur bahar aa jao |

Container ke **bahar** se judte waqt do aur lagte hain:

| Flag | Matlab |
|---|---|
| `-h localhost` | **h**ost |
| `-p 5440` | **p**ort — bahar wala. Andar se judte waqt nahi chahiye |
| `PGPASSWORD=calendar` | flag nahi, env hai — warna psql password poochta hai |

### Backslash commands — psql ke andar

SQL nahi, psql ke apne shortcut. Semicolon nahi lagta.

| Command | Matlab |
|---|---|
| `\dt` | **d**escribe **t**ables — saari tables |
| `\d calendar_event` | **d**escribe — ek table ke columns, types, indexes, constraints |
| `\q` | **q**uit |

Docker ke `run` wale flags (`-d`, `--name`, `-e`, `-p`) aur baaki sab
[`06-commands-reference.md`](06-commands-reference.md) me hain.

## Data dekhna — DBeaver se

GUI client container ka naam nahi jaanta — wo sirf **host aur port** se judta hai.
`campus-calendar-db` container ka naam hai; database ka naam `campus_calendar` hai.

### Screen 1 — "Connect to a database"

`Ctrl + Shift + N`, ya menu se `Database → New Database Connection`.

Driver ki grid khulti hai. Sabse upar-left wala **PostgreSQL** (haathi) chuno →
**Next >**.

> Grid me Hive/Oracle/MySQL sab dikhte hain. Upar ke search box me `postgres`
> likh doge to ek hi reh jaayega.

### Screen 2 — "Connection Settings", `Main` tab

| Field | Value |
|---|---|
| Host | `localhost` |
| **Port** | **`5440`** — default `5432` aata hai, **badalna hai** |
| **Database** | **`campus_calendar`** |
| Authentication | `Database Native` (jaisa hai waisa) |
| Username | `calendar` |
| Password | `calendar` |
| Save password | tick |

### Screen 3 — driver

Neeche-left **Test Connection …** dabao.

Pehli baar **"Download driver files"** ka popup aata hai → **Download**. DBeaver
PostgreSQL ka JDBC driver khud laata hai, ek hi baar.

Sahi hua to *"Connected"* aur server ka version dikh jaata hai.

### Screen 4 — Finish

**Finish** dabao. Left panel (Database Navigator) me nayi entry aa jaayegi.

Use kholte jao:

```
campus_calendar → Schemas → public → Tables
```

`calendar_settings` par double-click → **Data** tab → ek row dikhegi.

> DBeaver apni connections `~/.local/share/DBeaverData/workspace6/General/.dbeaver/data-sources.json`
> me rakhta hai aur **exit par us file ko dobara likh deta hai**. Haath se entry
> daalni ho to pehle DBeaver band karo.

## Roz ke commands

| Kaam | Command |
|---|---|
| Chalu | `docker start campus-calendar-db` |
| Band | `docker stop campus-calendar-db` |
| psql | `docker exec -it campus-calendar-db psql -U calendar -d campus_calendar` |
| Logs | `docker logs campus-calendar-db --tail 20` |
| **Poora uda do** | `docker rm -f campus-calendar-db` — data bhi jaayega |

> Data container ke andar hai, volume me nahi. POC ke liye theek hai. Data bachana
> ho to `-v campus_calendar_data:/var/lib/postgresql/data` laga kar banao.
