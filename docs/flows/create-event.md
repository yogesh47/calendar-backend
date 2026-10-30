# Create Event — line by line, frontend se DB tak

Ye file ek hi sawaal ka jawab hai: **TPO "Publish Event" dabata hai** (frontend me
do kadam: pehla generic step — title, date/time, repeat, remind, description →
**Next** → doosra step jahan event type chuna jaata hai, phir Publish), **uske baad
backend me exactly kya-kya chalta hai.** Har function, uske parameter, wo kya
karta hai, aur aage kise bulata hai — usi order me.

Sab line numbers aaj ke code ke hain.

---

## 0. Frontend kya bhejta hai

`calendar-frontend/src/modules/Calendar/services/api.ts` → `createEvent(draft)`
draft ko snake_case payload me badalta hai aur bhejta hai:

```
POST http://127.0.0.1:8001/calendar/events
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "event_type": "ppt",
  "title": "Quantum Dynamics PPT",
  "company": "Quantum Dynamics Inc.",
  "event_date": "2026-10-16",
  "end_date": "2026-10-16",
  "start_time": "14:00",
  "end_time": "15:00",
  "mode": "offline",
  "venue": "Auditorium, Block A",
  "online_platform": null,
  "description": "<p>Bring your resume</p>",
  "note": null,
  "audience": { "opportunity_type": "job", "courses": ["BTech"],
                "batches": [2027], "departments": ["Computer Science"] },
  "remind_before": "none",
  "linked_type": null,
  "linked_id": null,
  "linked_job": { "kind": "campus", "campus_job": "47 billion — SDE", "url": null, "title": null }
}
```

Time **IST** me jaata hai (`"14:00"`), date `YYYY-MM-DD`. UTC me badalna backend
ka kaam hai (step 4).

`event_type: "other"` ho to payload me `"other_type": "Alumni Meet"` bhi jaata hai
(TPO ka apna naam, max 80); baaki type par ye field `null` / nahi bhejte.

---

## 1. FastAPI route — `app/routes/calendar.py:44`

```python
@router.post("/events", response_model=EventOut, status_code=201)
def create_event(
    payload: EventIn,                                   # body → validate ho kar yahan
    user: HardcodedUser = Depends(calendar_user),       # JWT → kaun bhej raha hai
    db: Session = Depends(get_db),                      # DB session
) -> EventOut:
```

Teen parameter, teenon alag jagah se aate hain:

| Parameter | Kaun bharta hai | Kya hota hai pehle |
|---|---|---|
| `payload: EventIn` | FastAPI, body se | **Pydantic validation** — `app/models/calendar_model.py:38` |
| `user` | `calendar_user` dependency (`routes/calendar.py:24` → `auth/deps.py:27`) | Bearer token padha, `read_token()` se claims, `find_by_id()` se user; role TPO/student na ho to 403 |
| `db` | `app/db/session.py:17` `get_db()` | ek SQLAlchemy session, response ke baad band |

### 1a. `EventIn` validation — `app/models/calendar_model.py:54`

Field-level rules pehle: `title` 1–120 char, `venue` ≤200, `description` ≤1000,
`mode` sirf `offline`/`online`, date/time ka format.

Phir `@model_validator(mode="after") check_by_type()` (line 84) — **event type ke
hisaab se**:

* type list me hai? warna `"Unknown event type"`
* `other` hai to `other_type` (strip karke) khaali nahi hona chahiye, warna
  `"Specify the event type"` (field `other_type`, label "Event type name"; max 80
  ka field rule alag). Kisi aur type par `other_type = None` kar diya jaata hai
* timed type (ppt, company_visit, …) hai to `start_time`/`end_time` zaroori, aur
  end > start (cross-midnight ke liye `end_date` ko jod kar dekha jaata hai)
* mode wale type me `mode` zaroori; offline → `venue`, online → `online_platform`
* reminder chhod kar sab me audience ke teenon (course, batch, department) zaroori
* external linked job me `https://` wala url aur title zaroori

Koi bhi rule toote → FastAPI `RequestValidationError` → `app/errors.py:171` ka
handler ek **padhne-layak line** bana kar 422 bhejta hai
(`{"message": "Venue is required for an offline event", "code": "validation_error", "field": "venue", ...}`;
model-level message ka field `MODEL_FIELD_HINTS` se milta hai, jaise
"Specify the event type" → `other_type`) → frontend us box ko highlight karke toast
dikhata hai.

### 1b. Role guard — `routes/calendar.py:85`

```python
if payload.event_type != "my_reminder" and user.role != TPO:
    raise PermissionDeniedError("Only a TPO can create events")
```

Student sirf apna `my_reminder` bana sakta hai; baaki har type TPO ka.

---

## 2. Service — `app/services/calendar_service.py:278`

```python
created = calendar_service.create_event(db, user, payload)   # route line 52
```

```python
def create_event(db: Session, user: HardcodedUser, payload: EventIn) -> EventOut:
```

| Parameter | Kya hai |
|---|---|
| `db` | wahi session jo route ko mila |
| `user` | kaun bana raha hai — `org_id`, `user_id`, `role` isi se lete hain |
| `payload` | validate ho chuka `EventIn` |

### 2a. Reminder wala raasta — line 279

```python
if payload.event_type == "my_reminder":
    reminder = CalendarReminder(org_id=…, owner_id=user.user_id, owner_role=user.role, …)
    db.add(reminder); db.commit(); db.refresh(reminder)
    return reminder_out(reminder, user)
```

Reminder **alag table** (`calendar_reminder`) me jaata hai — na audience, na
recipients, na notification, na nudge. Yahin function khatam.

### 2b. Event wala raasta — line 298

```python
event = CalendarEvent(org_id=uuid.UUID(user.org_id), created_by=uuid.UUID(user.user_id))
apply_payload(event, payload)      # → step 3
db.add(event)
db.flush()                         # ← commit nahi; sirf event_id (PK) mil jaata hai
```

`db.flush()` isliye chahiye kyunki agli lines me `event.event_id` chahiye
(audience aur recipients usi par tangte hain), par abhi commit nahi karna.

---

## 3. `apply_payload(event, payload)` — line 258

Payload ke field ko DB column par rakhta hai (`event.other_type = payload.other_type`
bhi — validator ke baad wo sirf `other` par bhara hota hai, warna `None`). Do line khaas hain:

```python
event.company_id = company_id_of(payload.company)                        # → 3a
event.start_at   = to_utc(payload.event_date, payload.start_time)        # → 3b
event.end_at     = to_utc(payload.end_date or payload.event_date, payload.end_time)
```

### 3a. `company_id_of(name)` — `app/services/companies.py:14`

```python
return uuid.uuid5(COMPANY_NAMESPACE, name)     # naam → hamesha wahi uuid
```

Company ka apna table nahi hai; naam se **deterministic uuid5** bana kar store
karte hain, aur padhte waqt `company_name_of()` ulta map kar deta hai.

### 3b. `to_utc(day, wall_clock)` — `app/services/clock.py:9`

```python
datetime.combine(day, wall_clock, tzinfo=ORG_TIMEZONE).astimezone(timezone.utc)
```

Frontend ne IST bheja tha; DB me hamesha **UTC** jaata hai. Padhte waqt
`local_time()` / `local_date()` wapas IST me badal dete hain. Isi wajah se
05:30 IST = 00:00 UTC jaisa boundary case bhi theek rehta hai.

---

## 4. Audience row — service line 303

```python
if payload.audience:
    db.add(CalendarEventAudience(event_id=event.event_id, opportunity_type=…,
                                 courses=…, batches=…, departments=…))
    sync_recipients(db, event, payload.audience)        # → step 5
```

Audience ek alag row me rehti hai (kiske liye event hai), aur usi se recipients
nikalte hain (kis-kis student ko mila).

---

## 5. `sync_recipients(db, event, audience)` — line 233

```python
wanted   = set(matching_student_ids(audience.courses, audience.batches, audience.departments))
existing = { str(row.student_id): row for row in <is event ki saari recipient rows> }

for student_id in wanted - set(existing):          # naye student → nayi row
    db.add(CalendarEventRecipient(..., state="active"))

for student_id, row in existing.items():           # purane student
    row.state = "active" if student_id in wanted else "removed"
    if student_id not in wanted:
        row.seen_at = None                         # notification dobara "unread"
```

* **`matching_student_ids()`** — `app/services/students.py:25`. Demo me student
  profile hardcoded hai (BTech · 2027 · Computer Science); teenon match hue to
  student ki id list, warna khaali list.
* `state="removed"` wali row **delete nahi hoti** — isi se student ko BRD wala
  *"No longer applicable"* dikhta hai aur notification jaati hai.
* Ye function create aur update dono me chalta hai, isliye idempotent hai.

> Create me `notified_count` bhi yahin se banta hai: `audience_count()`
> (`students.py:16`) har course × batch × department ka deterministic
> `group_size()` jod kar ginti deta hai.

---

## 6. Commit — service line 315

```python
db.commit()        # event + audience + recipients, sab ek hi transaction me
db.refresh(event)  # DB ke defaults (created_at, updated_at, status) wapas object me
```

Yahan tak kuch bhi fail hua to **poora rollback** — aadha event kabhi nahi bachta.

---

## 7. `nudges.schedule_for_event(db, event)` — service line 317 → `app/services/nudges.py:76`

```python
_drop_scheduled(db, event.event_id)              # purane pending nudge hatao
if event.status != "published": db.commit(); return

settings   = settings_service.current_row(db)    # Super Admin ki values (FR-CAL-27)
recipients = <is event ke active recipients>

for recipient in recipients:
    if event.start_at:
        _add(..., EVENT_DAY_BEFORE,  event.start_at - timedelta(days=settings.event_reminder_days_before))
        _add(..., EVENT_HOUR_BEFORE, event.start_at - timedelta(hours=settings.event_reminder_hours_before))
    if event.event_type == "online_assessment":
        _add(..., ASSESSMENT_DAY, to_utc(event.event_date, time(8, 0)))
db.commit()
```

`_add()` (line 40) do cheezein dekhta hai: waqt nikal to nahi gaya
(`when <= now` → nudge banta hi nahi), aur wahi row pehle se to nahi hai.

Nudges ke aage ka poora rasta — kab bhejte hain, quiet hours, daily limit —
[`nudges.md`](nudges.md) me hai.

---

## 8. `event_out(db, event, user)` — service line 72

DB object ko API ke `EventOut` me badalta hai. Ismein:

* `company_name_of(event.company_id)` — uuid se naam wapas
* `local_time(event.start_at)` / `local_date(event.end_at)` — UTC se wapas IST
* `notified_count` — audience se gini hui ginti, warna
  `_recipient_count()` (line 60) jo sirf `state="active"` rows ginti hai
* `is_owner` — `event.created_by == viewer.user_id` (frontend isi se Edit/Cancel
  dikhata hai)
* `applies_to_me` / `removed_reason` — student ke liye uski apni recipient row se
  (`_recipient_of()`, line 68)

---

## 9. Live push — route line 53

```python
live_stream.publish(user.org_id, created.event_id)
```

`app/services/live_stream.py:20` — us org ke har khule SSE queue me event id daal
deta hai. Har khula calendar (`GET /calendar/stream`) turant `fetchEvents()`
dobara chalata hai, isliye doosri screen par bina refresh naya event aa jaata hai.

---

## 10. Response

Route `created` (ek `EventOut`) lautata hai, status **201**. Frontend
`api.ts` → `toEvent()` use camelCase `TpoEvent` me badalta hai, `CalendarPage`
list refresh karta hai aur toast dikhata hai:
*"Event published. 38 students notified."*

---

## Ek nazar me call chain

```
POST /calendar/events
└── routes/calendar.py:44  create_event(payload, user, db)
    ├── EventIn validation           models/calendar_model.py:54 → check_by_type():84
    │   └── fail → errors.py:171 → 422 {"message": "<ek line>", "field": …}
    ├── role guard (TPO?)            routes/calendar.py:85
    ├── services/calendar_service.py:278  create_event(db, user, payload)
    │   ├── my_reminder?  → CalendarReminder + commit → reminder_out()  [khatam]
    │   ├── CalendarEvent(org_id, created_by)
    │   ├── apply_payload(event, payload)                               :258
    │   │   ├── companies.company_id_of(name)                           companies.py:14
    │   │   └── clock.to_utc(date, time)  ×2                            clock.py:9
    │   ├── db.flush()                      → event_id mila
    │   ├── CalendarEventAudience(...)
    │   ├── sync_recipients(db, event, audience)                        :233
    │   │   └── students.matching_student_ids(...)                      students.py:25
    │   ├── db.commit() + db.refresh(event)
    │   ├── nudges.schedule_for_event(db, event)                        nudges.py:76
    │   │   ├── _drop_scheduled()                                       nudges.py:69
    │   │   ├── settings_service.current_row(db)                        settings_service.py:38
    │   │   └── _add(...) × (recipients × nudge types)                  nudges.py:40
    │   └── event_out(db, event, user)                                  :72
    │       ├── companies.company_name_of()
    │       ├── clock.local_time() / local_date()
    │       └── _recipient_count() / _recipient_of()
    ├── live_stream.publish(org_id, event_id)                           live_stream.py:20
    └── 201 + EventOut
```

## Kya-kya DB me likha jaata hai

| Table | Kitni rows | Kab |
|---|---|---|
| `calendar_event` | 1 | hamesha (reminder chhod kar) |
| `calendar_event_audience` | 1 | jab audience aayi ho |
| `calendar_event_recipient` | matching students jitni | `sync_recipients()` me |
| `calendar_nudge` | recipients × (1–3) | `schedule_for_event()` me, future wale hi |
| `calendar_reminder` | 1 | sirf `my_reminder` wale raaste me |
