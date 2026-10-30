# Nudges — end to end

BRD: **FR-CAL-25** (kaun se nudge), **FR-CAL-26** (rules), **FR-CAL-27** (Super Admin settings).

Nudge = system ki taraf se student ko bheja gaya apne-aap wala reminder. Ye TPO
ke action se aane wali notification se alag hai — notification TPO kuch karta hai
tab jaati hai, nudge **ghadi dekh kar** jaati hai.

---

## 1. Ek nazar me flow

```
TPO event banata hai
        │
        ▼
calendar_service.create_event()
        │  recipients bante hain (calendar_event_recipient)
        ▼
nudges.schedule_for_event()          ← har active recipient ke liye rows
        │
        ▼
calendar_nudge  (status = scheduled, scheduled_at = kab bhejna hai)
        │
        │   har 60 second
        ▼
nudges.run_due()                     ← background loop (app/main.py)
        │
        ├─ ab bhi relevant hai?   nahi → status = skipped
        ├─ quiet hours chal rahe? haan → scheduled_at = 7:00 AM (roka)
        ├─ aaj ka limit bacha?    nahi → status = skipped (limit reached)
        └─ haan                        → status = sent, sent_at = ab
        │
        ▼
student ko dikhta hai:
   • bell panel me            (GET /calendar/notifications)
   • calendar par purple tile (GET /calendar/events, event_type = "nudge")
   • Home feed card           (Dashboard)
```

---

## 2. Teen nudge, kab bhejte hain

| ID | nudge_type (DB) | Kab | Kis par | Message |
|---|---|---|---|---|
| **N-S1** | `event_day_before` | event start se **1 din** pehle | event ki audience ke student | `Reminder: [Title] tomorrow at [Time] · [Venue]` |
| **N-S1** | `event_hour_before` | event start se **1 ghanta** pehle | wahi | `[Title] starts in 1 hour · [Venue]` |
| **N-S3** | `assessment_day` | test wale din **8:00 AM** | `online_assessment` type ke event ki audience | `Your online test is today ([Start]–[End]). Check your email for the test link.` |
| **N-S2** | `deadline_days_before` | application band hone se **2 din** pehle, 9:00 AM | eligible student jisne apply nahi kiya | `[Company] [Job Title] applications close in 2 days` |
| **N-S2** | `deadline_last_day` | band hone wale **din** 9:00 AM | wahi | `Last day to apply: [Company] [Job Title]` |

"1 din", "1 ghanta", "2 din" aur "last day on/off" — ye **fixed nahi** hain, Super
Admin inhe `Calendar & Nudges` screen se badal sakta hai (neeche §4).

> Agar nudge ka waqt pehle hi nikal chuka hai to wo **banta hi nahi**
> (`_add()` me `when <= now` par return) — BRD: "that nudge is skipped".

---

## 3. Data kahan se aata hai (asli sawaal)

| Cheez | Source | File |
|---|---|---|
| Events, unka time, status (cancelled/published) | **Postgres** `calendar_event` | `app/db/models/calendar_event.py` |
| Kis student ko event mila (audience) | **Postgres** `calendar_event_recipient` (state `active` / `removed`) | `calendar_service.sync_recipients()` |
| Nudge ki har row — kab bhejni hai, bheji gayi ya nahi | **Postgres** `calendar_nudge` | `app/db/models/calendar_nudge.py` |
| Timings, daily limit, quiet hours | **Postgres** `calendar_settings` (Super Admin edit karta hai) | `app/services/settings_service.py` |
| Timezone (Asia/Kolkata) | env `DEFAULT_ORG_TIMEZONE` | `app/conf.py`, `app/services/clock.py` |
| Student kis course/batch/department ka hai | **Hardcoded** (demo) | `app/services/students.py` → `STUDENT_PROFILE` |
| Campus jobs aur unki last date | **Hardcoded** (demo) | `app/services/jobs.py` → `CAMPUS_JOBS` |

Yaani **nudge ka saara state DB me hai** — koi bhi nudge memory me nahi rakha
jaata, server restart ho to bhi scheduled rows waise ki waise rehti hain.

Sirf do cheezein hardcoded hain kyunki is demo app me unka apna service nahi hai:

* **student profile** — asli product me student DB se aata, yahan ek hi student
  hai (BTech · 2027 · Computer Science);
* **campus jobs + application end date** — asli product me Jobs service se aata,
  yahan frontend ke `services/jobs.ts` ki hubahu copy hai taaki calendar par
  dikhne wali deadline aur nudge dono ek hi date par rahein.

Dono jagah badalna ho to sirf wahi do file chhedni hoti hain; baaki engine waisa
hi chalta rahega.

---

## 4. Super Admin ke settings ka asar

`Calendar & Nudges` (login: `admin@campus.test`) me jo value save hoti hai wo
`calendar_settings` ki ek hi row me jaati hai, aur engine har tick par wahi row
padhta hai:

| Setting | Kahan lagta hai |
|---|---|
| Event Reminder: days before | `event_day_before` ka scheduled_at |
| Event Reminder: hours before | `event_hour_before` ka scheduled_at |
| Deadline Reminder: days before | `deadline_days_before` ka scheduled_at |
| Deadline Reminder: same day | `deadline_last_day` banega ya nahi |
| Daily nudge limit per student | ek din me kitne bhej sakte hain |
| Quiet hours | kis time window me rokna hai |

Settings badalne par **pehle se schedule** nudges wahin rehte hain (BRD: "Changes
apply only to nudges that haven't been scheduled yet"); agli baar event edit hone
par ya naye event par nayi timing lagti hai.

---

## 5. Bhejte waqt ke chaar filter (FR-CAL-26)

`nudges.run_due()` har due row par, isi order me:

1. **Ab bhi relevant hai?** — event delete/cancel ho gaya, ya student audience se
   nikal diya gaya, ya job list me nahi raha → `status = skipped`, `skip_reason`
   likh dete hain.
2. **Quiet hours** — local time 10:00 PM–7:00 AM ke beech hai to row ka
   `scheduled_at` 7:00 AM par shift ho jaata hai (bheja nahi jaata).
   **Exception:** `event_hour_before` — event hi raat ko ho to wo roka nahi jaata.
3. **Daily limit** — us student ke aaj ke `sent` nudges gine jaate hain. Jagah
   kam padi to priority: **deadline (1) > assessment (2) > event reminder (3)**;
   neeche wale `skip_reason = "Daily nudge limit reached"` ke saath drop.
4. **Bhejo** — `status = sent`, `sent_at = ab`. DB ka unique constraint
   `(student_id, nudge_type, item_id, scheduled_at)` dobara bhejne nahi deta.

Date badal jaaye to? Event update hone par us event ke **saare pending** nudges
delete karke nayi date par dobara bante hain (`schedule_for_event()` ka pehla kaam
`_drop_scheduled()` hai). `sent` wale history ki tarah bache rehte hain.

Type badal jaaye to? Edit par event ek type se doosre me ja sakta hai (sirf
`my_reminder` me nahi — wo 403). Wahi `schedule_for_event()` naye type se nudges
banata hai — jaise `training` → `online_assessment` par `assessment_day` (8:00 AM)
jud jaata hai, ulta karne par hat jaata hai; deadline (bina time) par
`event_day_before` / `event_hour_before` nahi bante.

---

## 6. Background loop

`app/main.py` ka `nudge_loop()`:

```
har NUDGE_TICK_SECONDS (default 60) par
    nudges.schedule_deadlines(db, org)   ← job deadlines ke nudges (idempotent)
    nudges.run_due(db)                   ← jo due ho gaye wo bhejo
    kuch bheja? → live_stream.publish()  ← khule hue calendar turant refresh
```

Loop app ke startup par chalu hota hai aur shutdown par cancel. Koi error aaye to
loop marta nahi — agle tick par phir koshish karta hai.

---

## 7. Student ko kahan dikhta hai

| Jagah | Kaise aata hai |
|---|---|
| Bell panel | `GET /calendar/notifications` — `sent` nudges bhi usi list me, `is_read` nudge ke apne `seen_at` se |
| Calendar tile | `GET /calendar/events` — har `sent` nudge ek item, `event_type: "nudge"`, purple "Reminder" style, jis din bheja gaya usi din par |
| Home feed | Dashboard wahi notification list padh kar cards banata hai |

Nudge item read-only hai — usme Edit/Delete nahi, sirf related event/job par
jaane ka rasta.

---

## 8. Khud test karna ho

```bash
cd calendar-backend && . .venv/bin/activate
PYTHONPATH=. python - <<'PY'
from app.db.session import SessionLocal
from app.services import nudges
with SessionLocal() as db:
    print(nudges.run_due(db))        # {'sent': n, 'skipped': n, 'held': n}
PY
```

Sab rows dekhne ke liye:

```bash
docker exec campus-calendar-db psql -U calendar -d campus_calendar \
  -c "select nudge_type, status, scheduled_at, sent_at, skip_reason from calendar_nudge order by scheduled_at;"
```
