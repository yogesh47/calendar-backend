# Step 3 — Tables

## Kaun si 6 tables

Design doc §5 ke hisaab se, `app/db/models.py` me:

| Table | Kya rakhti hai |
|---|---|
| `calendar_event` | event — type, title, date, mode, venue, status, cancel ka byora |
| `calendar_event_audience` | ek event ka ek row — courses, batches, departments |
| `calendar_event_recipient` | publish par freeze hui student list, `active` / `removed` |
| `calendar_reminder` | TPO aur student dono ke My Reminders |
| `calendar_nudge` | kis student ko kab nudge jaana hai |
| `calendar_settings` | **poore platform ki ek hi row** — isi liye ispar `org_id` nahi |

**Application Deadline ki koi table nahi.** Wo jobs API ki expiry date se derive
hoti hai — design ka pehla na-badalne-wala faisla.

## Teen baatein jo models me jaan-boojh kar hain

| Baat | Kyun |
|---|---|
| `student_id`, `company_id`, job ids par **FK nahi** | wo rows hamare DB me hain hi nahi — SkillsBridge ki hain |
| `event_date` `Date` hai, `timestamp` nahi | all-day cheez ka din timezone se nahi badalna chahiye (§3) |
| `start_at` / `end_at` `DateTime(timezone=True)` | DB me UTC, render user ke timezone me |

## Unique constraints — inhi se galti rukti hai

| Table | Constraint | Kya rokta hai |
|---|---|---|
| `calendar_event_recipient` | `(event_id, student_id)` | ek student ek event me do baar |
| `calendar_nudge` | `(student_id, nudge_type, item_id, scheduled_at)` | **double-send** |
| `calendar_event_audience` | `event_id` unique | ek event ke do audience |

## Indexes

| Index | Kiske liye |
|---|---|
| `ix_calendar_event_org_date` | mahine ka calendar ek query me |
| `ix_calendar_event_org_status` | sirf published nikalna |
| `ix_calendar_recipient_student` | student ko apne event dikhana |
| `ix_calendar_nudge_due` | scheduler ko due nudges |
| `ix_calendar_reminder_owner_date` | My Reminders |

## Banane ka command

```bash
cd calendar-backend
source .venv/bin/activate
PYTHONPATH=. python scripts/init_db.py
```

```
tables ready: calendar_event, calendar_event_audience, calendar_event_recipient,
              calendar_nudge, calendar_reminder, calendar_settings
settings row created
```

`PYTHONPATH=.` zaroori hai — warna `No module named 'app'` aata hai.

Script do kaam karti hai:

1. `Base.metadata.create_all(engine)` — jo table nahi hai wahi banti hai
2. `calendar_settings` me **ek row** daalti hai, agar pehle se nahi hai

Dobara chalao to kuch nahi tootta — row pehle se ho to chhod deti hai.

## Jaanchne ke commands

```bash
docker exec campus-calendar-db psql -U calendar -d campus_calendar -c "\dt"
docker exec campus-calendar-db psql -U calendar -d campus_calendar -c "\d calendar_event"
docker exec campus-calendar-db psql -U calendar -d campus_calendar \
  -c "select daily_nudge_limit, quiet_hours_start, quiet_hours_end from calendar_settings;"
```

## Settings ki default row

| Column | Default |
|---|---|
| `event_reminder_days_before` | 1 |
| `event_reminder_hours_before` | 1 |
| `deadline_reminder_days_before` | 2 |
| `deadline_reminder_same_day` | true |
| `daily_nudge_limit` | 3 |
| `quiet_hours_start` | 22:00 |
| `quiet_hours_end` | 07:00 |

## Migrations ke baare me

Abhi `create_all` chal raha hai, jo POC ke liye theek hai. Jaise hi schema
badalna shuru ho, **Alembic** laga lena — `create_all` purani table ko badalta
nahi, sirf nayi banata hai.
