# Backend — setup aur run

Postgres container chalta hona chahiye:

```bash
make db-init      # sirf pehli baar — container banata hai (port 5440)
make db-start     # uske baad har baar
```

---

## 1. Install (sirf pehli baar)

```bash
cd calendar-backend

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

> Server (dev / stage / prod) par `.env` mein `PUBLIC_API_URL` bharna — jaise
> `https://dev.7seers.ai` (koi path prefix ho to wo bhi). Calendar Sync ka link isi
> se banta hai; Google aur Outlook apne server se ye link kholte hain, isliye
> `127.0.0.1` ya proxy ka andar ka address unke liye bekaar hai. Local par khaali chhodo.

---

## 2. DB check karo

```bash
make db-check
```

**Mil gaya:**

```
DB CONNECTION SUCCESSFUL
  db     : campus_calendar
  tables : 8
```

→ kuch karne ki zaroorat nahi, seedha step 3.

**Nahi mila:**

```
DB CONNECTION FAILED
  reason : OperationalError: ... database "campus_calendar" does not exist
```

→ bana lo:

```bash
make db-up
```

Ye database banata hai, saari Alembic migrations (`initial setup` se head
`a1c4e7f2b905` tak) chala kar tables/columns banata hai, aur settings ki ek
default row daalta hai.

> DB pehle se hai par code pull kiya jisme nayi migration hai (jaise
> `a1c4e7f2b905_other_event_type_name` — `calendar_event.other_type`)? Tab bhi
> bas `make db-up` — sirf pending migrations chalti hain, data waisa hi rehta hai.

Sab kuch mitana ho:

```bash
make db-drop     # database delete
make db-up       # wapas naya, data khali
```

---

## 3. Backend chalao

```bash
make run
```

API: **http://127.0.0.1:8001** · Swagger: **/docs**

Check:

```bash
curl http://127.0.0.1:8001/health
# {"status":"ok","database":"up"}
```

Terminal khula chhod do — band karoge to API band.

---

## 4. Kaam khatam — container band karo

```bash
make db-stop      # Postgres container band
```

Agli baar bas `make db-start` → `make run`.

---

## Commands

| Command | Kaam |
|---|---|
| `make db-init` | Postgres container banao (sirf pehli baar) |
| `make db-start` | container chalu |
| `make db-stop` | container band |
| `make db-check` | DB judta hai ya nahi, kitni tables hain |
| `make db-up` | database + pending migrations + settings row (pull ke baad bhi chalao) |
| `make db-drop` | database delete |
| `make run` | API chalu (port 8001; purana server pehle band ho jaata hai) |
| `make db-revision m="..."` | nayi migration — [`migrations.md`](migrations.md) |
