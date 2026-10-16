# DB drop aur up — do command

```bash
cd calendar-backend

make db-drop     # database delete
make db-up       # database + saari tables + settings row (data khali)
```

venv activate karne ki zaroorat nahi — `Makefile` khud `.venv/bin/python` use
karta hai. Postgres container chalta rehna chahiye (`make db-start`).

---

## `make db-drop` kya karta hai

`setup/drop_db.py --yes`

1. `.env` ke `DATABASE_URL` se database ka naam nikalta hai (`campus_calendar`)
2. us database se judi **sab connections band** karta hai (`pg_terminate_backend`) —
   warna Postgres drop nahi karne deta
3. `drop database if exists campus_calendar`

```
database deleted: campus_calendar
wapas banane ke liye: make db-up
```

> Script bina `--yes` ke kuch nahi karti, taaki galti se na chal jaye. `make db-drop`
> ye flag khud laga deta hai.

---

## `make db-up` kya karta hai

`setup/init_db.py`

1. database na ho to **bana deta hai**
2. **Alembic migration** `initial setup` chalata hai → saari **7 tables**, unke
   indexes aur constraints
3. `calendar_settings` me **ek default row** daalta hai — 1 din + 1 ghanta pehle
   reminder, deadline 2 din pehle + last day on, daily limit 3, quiet hours
   22:00–07:00

```
Running upgrade  -> 8e5c071131a6, initial setup — every table the calendar needs
database created: campus_calendar
schema is up to date
tables: calendar_event, calendar_event_audience, calendar_event_recipient,
        calendar_nudge, calendar_push_device, calendar_reminder, calendar_settings
settings row created
```

Users kahin seed nahi hote — wo `app/auth/users.py` me hain, isliye login turant
chalu (`tpo@campus.test` / `tpo@1234` wagairah).

---

## Poora DB nahi udana, sirf data mitana ho

**UI se:** TPO se login → Campus Calendar → **Delete all**.

**API se** (org ke events + isi user ke reminders):

```bash
API=http://127.0.0.1:8001
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"tpo@campus.test","password":"tpo@1234"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -X DELETE "$API/calendar/events?confirm=yes" -H "Authorization: Bearer $TOKEN"
```

**SQL se** (sab kuch, settings bachi rahegi):

```bash
docker exec campus-calendar-db psql -U calendar -d campus_calendar -c "
truncate calendar_event, calendar_event_audience, calendar_event_recipient,
         calendar_reminder, calendar_nudge, calendar_push_device
restart identity cascade;"
```

Sirf nudges hatane hon: `delete from calendar_nudge;`

---

## Baaki baatein

| Sawaal | Jawab |
|---|---|
| API chal rahi ho to? | chalne do — drop par uska connection band hota hai, agli request par khud judh jaata hai |
| Check kaise karun | `curl http://127.0.0.1:8001/health` → `{"status":"ok","database":"up"}` |
| Bina `make` ke | `PYTHONPATH=. .venv/bin/python setup/drop_db.py --yes` · `PYTHONPATH=. .venv/bin/python setup/init_db.py` |
| Naya column joda hai | [`migrations.md`](migrations.md) — `make db-revision m="..."` phir `make db-up` |
| Tables kahan define hain | `app/db/models/` — detail [`../docs/schema.md`](../docs/schema.md) me |
