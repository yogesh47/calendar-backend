# Create Event: backend ka waterfall (mota-mota)

Frontend jab **"Publish Event"** dabata hai, to backend me kya-kya hota hai, kis order me, aur
data kahan-kahan jaata hai. Sirf backend ki baat hai.

> Line-by-line detail chahiye to: [`create-event.md`](create-event.md).
> Nudges kaise jaate hain: [`nudges.md`](nudges.md).

---

## 1. Ek nazar me

```
Frontend: POST /calendar/events
          header: Authorization: Bearer <token>
          body:   { event_type, title, event_date, start_time, end_time, mode, venue, audience, … }
   │
   ▼
① Route mila ─────────────── app/routes/calendar.py:78  @router.post("/events")
   │   FastAPI function chalane se PEHLE uski "zaroorat" (Depends) poori karta hai:
   │
   ├─② Login + DB session ──── app/db/session.py → get_db()
   │                            app/auth/deps.py  → current_user() → require_role(TPO, STUDENT)
   │      token nahi / galat / expire / user band?        → 401  (body dekhi bhi nahi jaati)
   │      Super Admin?                                     → 403
   │
   ├─③ Body check (Pydantic) ─ app/models/calendar_model.py → EventIn + check_by_type()
   │      field galat / adhoora / type ke niyam toote?     → 422  (pehli galti ka message)
   │
   ├─④ Role (function ke andar) ─ routes/calendar.py:84
   │      student ne event banaya (My Reminder nahi)?      → 403 "Only a TPO can create events"
   │
   ▼
⑤ Service ───────────────── app/services/calendar_service.py:404 → create_event()
   │   ┌──────────── EK TRANSACTION: ya sab save, ya kuch nahi ────────────┐
   │   │                                                                    │
   ├─⑥ Kitni dates? ─────── recurrence.occurrences()   repeat nahi → [1 date]
   │   │                                                                    │
   │   │  har date ke liye:                                                 │
   ├─⑦ Event row ─────────── apply_payload()          → calendar_event      │
   │   │     time → UTC ───── to_utc("10:00", Asia/Kolkata) = 04:30 UTC     │
   │   │     db.add + db.flush → event_id mil gaya                           │
   ├─⑧ Audience ──────────── _set_audience()          → calendar_event_audience
   ├─⑨ Students ──────────── sync_recipients()        → calendar_event_recipient (har student 1 row)
   │   │     db.flush → agle kadam ko students dikhein                       │
   ├─⑩ Reminders ─────────── schedule_for_event()     → calendar_nudge (scheduled)
   │   │                                                                    │
   ├─⑪ db.commit() ───────── sab ek saath pakka                             │
   │   │     beech me error? → db.rollback(), kuch nahi bacha → 422/403/503 │
   │   └────────────────────────────────────────────────────────────────────┘
   │
   ├─ jawab ka shape ──────── event_out(): UTC → campus time, company id → naam, notified_count
   ▼
⑫ Live update ───────────── app/services/live_stream.py → publish(org_id, event_id)
   │   us college ke har khule calendar ko signal
   ▼
⑬ 201 Created + EventOut
   │
   ═══════════ request khatam; aage ka kaam baad me, apne-aap ═══════════
   │
   ├─ khule calendar → GET /calendar/events          → naya event screen par
   ├─ student bell   → GET /calendar/notifications   → "New event: …" (recipient row se, padhte waqt)
   └─ har 60 second  → nudges.run_due()              → jinka time aaya, wo reminder bhejo
```

**Order ka sabak:** FastAPI pehle `Depends` (session aur login) poore karta hai, phir body jaanchta hai. Isliye bina token ki galat body par bhi **401** aata hai, 422 nahi. Ye maine chala kar dekha:

| Request | Jawab |
|---|---|
| Token nahi, body bhi galat | **401** "Sign in to continue" |
| Student ka token, body adhoori | **422** "Title is required" (+ `errors` me saari galtiyan) |
| Student ka token, body sahi PPT | **403** "Only a TPO can create events" |

---

### Har kadam: thoda code, thodi theory

**① Route mila**

```python
@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventIn,                                       # ③ body
    user: Annotated[SignedInUser, Depends(calendar_user)],  # ② login + role
    db: Annotated[Session, Depends(get_db)],                # ② DB session
) -> EventOut:
```

*Theory:* FastAPI parameters ko dekh kar samajhta hai ki kya chahiye. Typed parameter (`EventIn`) = JSON body. `Depends(...)` = pehle ye function chalao, uska nateeja do. Jo bhi fail ho, route ka function chalta hi nahi. `status_code=201` = "naya bana".

**② Login + DB session**

```python
def get_db():
    db = SessionLocal()          # is request ka apna session
    try:
        yield db                 # route ko do, khatam hone tak ruko
    except Exception:
        db.rollback()            # error aaya → aadha likha mitao
        raise
    finally:
        db.close()               # hamesha band

def current_user(credentials, db):
    if credentials is None:           raise AuthenticationError("Sign in to continue")   # 401
    claims = read_token(credentials.credentials)                                        # JWT kholo
    if not claims:                    raise AuthenticationError("Your session has expired")
    user = find_by_id(db, claims["sub"])                                                # DB se dobara
    if not user:                      raise AuthenticationError("Your session has expired")
    return user
```

*Theory:* **Session** = DB ki kachchi copy. Badlav `commit` tak pakke nahi hote, isliye error par sab mitaya ja sakta hai. **JWT** = login par mila signed token, jisme user id hai. Use sirf maana nahi jaata, user ko **DB se dobara** dekha jaata hai, taaki band kiya account purane token se na ghus sake. `require_role(TPO, STUDENT)` iske upar role ki chhalni hai.

**③ Body check**

```python
class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    event_date: date
    start_time: time | None = None
    mode: Literal["offline", "online"] | None = None
    audience: AudienceIn | None = None
    …
    @model_validator(mode="after")
    def check_by_type(self):
        if self.event_type in TIMED_TYPES and (not self.start_time or not self.end_time):
            raise ValueError("Start time is required for this event type")   # end time ke liye alag message
        if self.event_type in MODE_TYPES and self.mode == "offline" and not self.venue:
            raise ValueError("Venue is required for an offline event")
        …
```

*Theory:* **Pydantic** JSON ko Python object me badalta hai aur har field ka type / lambai jaanchta hai. Galat type (jaise date ki jagah "abc") → apne-aap error. Phir `check_by_type` type ke **hisab wale niyam** lagata hai: PPT ko time chahiye, offline ko venue, "Other" ko naam. Koi bhi galti → **422**, aur frontend ko `field` bhi milta hai, taaki wo sahi box ke neeche error dikha sake.

**④ Role**

```python
if payload.event_type != "my_reminder" and user.role != TPO:
    raise PermissionDeniedError("Only a TPO can create events")      # 403
```

*Theory:* Route tak TPO aur student dono aa sakte hain (dono ko reminder banana hai). Event banana sirf TPO ka kaam hai, aur ye check body padhne ke baad hi ho sakta hai, kyunki type body me hai.

**⑤–⑪ Service: ek transaction**

```python
days = recurrence.occurrences(...) if payload.recurrence else [payload.event_date]   # ⑥
for day in days:
    event = CalendarEvent(org_id=org_id, created_by=owner_id, recurrence=rule)
    apply_payload(event, _shifted(payload, day), payload.time_zone or org_zone(...)) # ⑦
    db.add(event)          # list me daalo
    db.flush()             # DB ko dikhao → event_id mila
    if payload.audience:
        _set_audience(db, event, payload.audience)                                   # ⑧ + ⑨
    nudges.schedule_for_event(db, event)                                             # ⑩
db.commit()                # ⑪ sab pakka
…
except Exception:
    db.rollback()          # kuch bhi toota → sab mitao
    raise
```

*Theory:* **Transaction** = kai kaam jo ek saath hote hain ya ek saath nahi hote. Event bana aur students nahi jude, aisi aadhi halat kabhi nahi banti. `flush` isliye chahiye ki audience, students aur nudges ko `event_id` chahiye, jo DB row bhejne par hi deta hai. `commit` sirf ek baar, sab ke end me.

**⑦ Time ko UTC me**

```python
event.start_at = to_utc(payload.event_date, payload.start_time, zone)
# to_utc: datetime.combine(day, wall_clock, tzinfo=zone).astimezone(timezone.utc)
# 20 Nov 10:00 Asia/Kolkata  →  20 Nov 04:30 UTC
```

*Theory:* DB me time hamesha **UTC** me, ek hi ghadi. Har dekhne wala use apne zone me dekhta hai (New York ka student ise 19 Nov, 11:30 PM EST dekhega). Event kis zone me likha gaya (`time_zone`), wo bhi saath save hota hai, taaki "Campus time" dikha sakein.

**⑨ Students**

```python
wanted = set(matching_student_ids(db, org_id, courses, batches, departments))
for student_id in wanted - set(existing):
    db.add(CalendarEventRecipient(event_id=event.event_id, student_id=student_id, state="active"))
```

*Theory:* Har student ki **ek row** = "ye event iske liye hai". Bell ka message, unread dot aur calendar par dikhna, sab isi row se chalta hai. Notification alag table me save nahi hoti; padhte waqt isi row se banti hai.

**⑩ Reminders**

```python
_add(..., EVENT_DAY_BEFORE,  when=event.start_at - timedelta(days=settings.event_reminder_days_before))
_add(..., EVENT_HOUR_BEFORE, when=event.start_at - timedelta(hours=settings.event_reminder_hours_before))
# _add: time nikal chuka → mat banao · bilkul yahi pehle se hai → mat banao · warna status = "scheduled"
```

*Theory:* Abhi **bheja nahi jaata**, sirf likh ke rakha jaata hai (`scheduled`). Ek background loop har 60 second due rows uthata hai, aur bhejne se pehle dobara jaanchta hai: cancel to nahi hua, quiet hours, daily limit.

**⑫ Live update**

```python
def publish(org_id, message):
    for queue in _listeners.get(org_id, set()):              # us college ke khule calendars
        _loops[queue].call_soon_threadsafe(queue.put_nowait, message)
```

*Theory:* Jo bhi calendar khula hai, uska browser ek **SSE** connection (`GET /calendar/stream`) khula rakhta hai. Server us par chhota sa message bhejta hai, aur browser events dobara le leta hai. Isliye refresh nahi karna padta.

> Har line ka poora matlab, asli line numbers ke saath: [`create-event-code.md`](create-event-code.md).

---

## 2. Har kadam, mota-mota matlab

| # | Kadam | Kahan | Kya hota hai (seedhi bhasha me) | Fail ho to |
|---|---|---|---|---|
| ① | Route | `routes/calendar.py` → `create_event()` | Darwaza. Request yahan aati hai | — |
| ② | Login + session | `db/session.py` → `get_db()`, `auth/deps.py` → `current_user()` | DB session khulta hai. Token padho, phir user ko **DB se** dobara dekho, taaki band kiya account token ke saath na ghus sake. **Body se pehle** hota hai | **401** |
| ③ | Body check | `models/calendar_model.py` → `EventIn` | Form ki jaanch: title (1–120), date, type sahi hai? Timed type par start / end time, end start ke baad. Offline par venue, online par platform. "Other" par naam (max 80). Audience aadhi nahi honi chahiye. Time zone sahi | **422** + `message` |
| ④ | Role | route | Event sirf **TPO** bana sakta hai. Student sirf apna **My Reminder** | **403** "Only a TPO can create events" |
| ⑤ | Service | `services/calendar_service.py` → `create_event()` | Asli kaam. Sab kuch **ek transaction** me | — |
| ⑥ | Repeat | `services/recurrence.py` → `occurrences()` | Repeat nahi to 1 date. Repeat hai (daily / weekly / monthly, until) to har date ki list. Ek saal se lamba repeat ③ par hi 422 | — |
| ⑦ | Event row | `apply_payload()` | Har date ke liye **ek row** `calendar_event` me: type, title, company, venue, image. Time ko **campus zone** (Asia/Kolkata) se **UTC** me badal kar `start_at` / `end_at`. Repeat ho to sab rows ek `series_id` share karti hain | DB error → rollback |
| ⑧ | Audience | `_set_audience()` | "Kiske liye": Opportunity → Course → Batch → Department, `calendar_event_audience` me. Audience khali chhoda to event bana, par abhi kisi student ko nahi gaya. Baad me event se chuna ja sakta hai | — |
| ⑨ | Students | `sync_recipients()` → `students.py` | Audience se mel khaane wale **har student ki ek row** `calendar_event_recipient` me (`state = active`). **Notification isi row se banti hai**, alag se save nahi hoti | — |
| ⑩ | Nudges | `services/nudges.py` → `schedule_for_event()` | Har student ke liye aage ke reminder **schedule** (abhi bheje nahi jaate): 1 din pehle, 1 ghanta pehle. Online Assessment par test wale din subah 8 baje (student ke apne zone me). Kitna pehle, ye Super Admin ki setting se. Jinka time nikal chuka, wo banenge hi nahi | — |
| ⑪ | Commit | `db.commit()` | Sab tables **ek saath** save. Beech me kuch bhi toota to **rollback**: na aadha event, na aadhe students | **503** (DB) / **500** (kuch aur) |
| ⑫ | Live update | `services/live_stream.py` → `publish()` | Us college ke jitne calendar khule hain (SSE `/calendar/stream`), sabko signal. Wo khud dobara load kar lete hain, refresh nahi karna padta | — |
| ⑬ | Jawab | `event_out()` | **201** + naya event (pehli date wala), `notified_count` ke saath | — |

---

## 3. Request ke baad (async, apne-aap)

| Kab | Kya | Kahan |
|---|---|---|
| Turant | Khule calendars ko signal mila → `GET /calendar/events` → naya event dikha | `live_stream.stream()` |
| Jab student bell khole | `GET /calendar/notifications` → recipient row se message banta hai: "New event: Deloitte PPT on 5 Nov, 10:00 AM." | `calendar_service` (notifications list) |
| Har 60 second | Background loop due nudges uthata hai: relevant hai? quiet hours? daily limit? → `sent` ya `skipped` | `app/main.py` → `nudges.run_due()` |
| Calendar sync (Google / Outlook) | Apne waqt par `.ics` feed dobara padhte hain → naya event wahan bhi aata hai | `GET /calendar/feed.ics` |

**Abhi nahi hota:** phone push aur email. Backend me device register karne ki API hai, par bhejne wala code abhi nahi hai.

---

## 4. Data kahan-kahan gaya (ek event, 1 date, 120 students)

| Table | Kitni rows | Kya |
|---|---|---|
| `calendar_event` | 1 (repeat ho to har date ki 1) | Event khud |
| `calendar_event_audience` | 1 per event row | Kiske liye (groups) |
| `calendar_event_recipient` | 120 | Har student ki ek; isi se bell ka message aur "read / unread" |
| `calendar_nudge` | ~240 (online test par ~360) | Har student ke 2 reminder (+ test wale din ka) `scheduled` |

---

## 5. My Reminder ka chhota rasta

Body me `event_type = "my_reminder"` ho, to kadam ② ③ wahi rehte hain, aur ④ me TPO aur student dono allow hain. Uske baad:

```
⑥ repeat ki dates → har date: ek row calendar_reminder  (audience / students nahi, private)
                  → nudges.schedule_for_reminder(): chune hue time par "reminder_alert"
⑪ commit → ⑫ live update → ⑬ 201
```

Reminder ka time **user ke apne zone** me save hota hai, campus zone me nahi. Uske alert par daily limit aur quiet hours **nahi** lagte.

---

## 6. Errors ek jagah

| Code | Kab | Kahan se |
|---|---|---|
| 401 | Token nahi / expire / user nahi (ye **pehle** check hota hai) | `current_user()` |
| 422 | Body galat (field missing, galat type, "Other" ka naam nahi, end start se pehle…) | `EventIn` → `errors.py` (`on_invalid_request`) |
| 403 | Student event banane ki koshish kare | route |
| 503 | DB me kuch toota (rollback ho chuka hota hai) | `errors.py` (`on_db_error`) |
| 500 | Koi aur anjaan error | `errors.py` (`on_unexpected`) |

Har error ka body ek jaisa hai: `{ "message": "…" }`.

---

## 7. Udaharan: TPO ne ek PPT banaya (dummy data, asli run)

Ye values POC par sach me ek PPT bana kar padhi gayi hain (2 Nov 2026), aur baad me event hata diya gaya.

**Frontend ne kya bheja** (`POST /calendar/events`, TPO Priya Sharma ke token se):

```json
{
  "event_type": "ppt",
  "title": "Deloitte Pre-Placement Talk",
  "company": "47 billion",
  "event_date": "2026-11-20", "end_date": "2026-11-20",
  "start_time": "10:00", "end_time": "11:30",
  "time_zone": "Asia/Kolkata",
  "mode": "offline", "venue": "Auditorium, Block A",
  "description": "<p>Company overview and the hiring process.</p>",
  "audience": { "opportunity_type": "job", "courses": ["BTech"], "batches": [2027], "departments": ["Computer Science"] },
  "remind_before": "none"
}
```

**Har kadam par kya hua:**

| # | Kadam | Is PPT ke saath |
|---|---|---|
| ② | Login | Token se user mila: Priya Sharma, role `tpo` ✅ |
| ③ | Body check | PPT ek **timed** type hai, to start / end time zaroori: 10:00 aur 11:30 diye, end start ke baad ✅. Mode `offline` hai, to venue zaroori: "Auditorium, Block A" ✅. Audience poori hai ✅ |
| ④ | Role | PPT event hai, banane wala TPO ✅ |
| ⑥ | Repeat | `recurrence` nahi bheja → sirf **1 date** (20 Nov) |
| ⑦ | Event row | `calendar_event` me 1 row. **10:00 IST → 04:30 UTC** (`start_at = 2026-11-20 04:30+00`), **11:30 IST → 06:00 UTC**. Company "47 billion" ka naam nahi, uska **id** (`company_id`) save hua. `status = published`, `series_id` khaali (repeat nahi) |
| ⑧ | Audience | `calendar_event_audience`: job · BTech · 2027 · Computer Science |
| ⑨ | Students | Audience se mel khaane wala **1 student account** mila (POC me ek hi student login hai) → `calendar_event_recipient` me 1 row, `state = active`, `seen_at` khaali (abhi padha nahi) |
| ⑩ | Nudges | `calendar_nudge` me 2 row, dono `scheduled`: **1 din pehle** → 19 Nov 04:30 UTC (= 19 Nov 10:00 IST), **1 ghanta pehle** → 20 Nov 03:30 UTC (= 20 Nov 9:00 IST). PPT online test nahi hai, isliye subah 8 baje wala reminder nahi bana |
| ⑪ | Commit | Upar ki saari rows ek saath save |
| ⑫ | Live update | Khule calendars ko signal → wahan PPT dikh gaya |
| ⑬ | Jawab | **201**, `event_id`, `starts_at: 2026-11-20T04:30:00Z`, `status: published`, `notified_count: 38`, `created_by_name: Priya Sharma` |

**Student ki bell me** (jab usne kholi): *"New event: Deloitte Pre-Placement Talk on 20 Nov, 10:00 IST. Check your calendar."*, unread.

**Aage kya hoga:** 19 Nov 10:00 IST aur 20 Nov 9:00 IST par background loop in dono nudges ko bhejega, agar tab tak event cancel na hua ho, student audience me ho, aur quiet hours / daily limit ijazat dein.

> **`notified_count` 38 kyo, jabki student row 1 hai?** 38 POC ki **dummy class size** hai
> (`services/students.py` → `group_size()`: B.Tech · 2027 · CSE = 38). Rows sirf **asli login wale**
> students ki banti hain, aur POC me ek hi student account hai. Asli project me student list
> Student service se aayegi, aur dono ginti ek hogi.

---

## 8. DB ke shabd, mota-mota matlab

Backend SQLAlchemy ka **session** (`db`) use karta hai. Session ek **kachchi copy** ki tarah hai: jo badlav karo, wo pehle session me rehte hain, aur `commit` par hi DB me pakke hote hain.

| Shabd | Mota-mota matlab | Create Event me kahan |
|---|---|---|
| `SessionLocal()` / `get_db()` | Har request ke liye DB se ek nayi baat-cheet (session) kholna, aur request khatam hote hi band karna. Beech me error aaye to `get_db` khud rollback karta hai | Route ka `db` yahin se aata hai |
| `db.add(row)` | "Ye nayi row save karni hai" ki **list me daalna**. Abhi DB me kuch nahi gaya | Event, audience, har student, har nudge |
| `db.flush()` | Ab tak ki list DB ko **bhej do, par pakka mat karo**. Isse DB naya id de deta hai (jaise `event_id`), jo aage chahiye. Galti hui to abhi bhi `rollback` se sab mit sakta hai | Event row ke baad (id chahiye, taaki audience / students / nudges usse jud sakein) |
| `db.commit()` | Sab badlav **pakke** kar do. Ab doosre log bhi dekh sakte hain, aur wapas nahi hota | Kadam ⑪, ek hi baar, sab ke aakhir me |
| `db.rollback()` | Commit se pehle ke saare badlav **mita do**, jaise kabhi hue hi nahi | Beech me kuch bhi toota to |
| `db.refresh(row)` | Commit ke baad row ko DB se **dobara padho**, taaki DB ki banayi values (jaise `created_at`) mil jaayein | Jawab banane se pehle (`first`) |
| `db.get(Model, id)` | Primary key se **ek row** lao (nahi mili to `None`) | Edit, delete, test me |
| `db.scalars(select(...))` | Query chala kar **kai rows** lao | Recipients, nudges padhna |
| `db.scalar(select(...))` | Query chala kar **pehli ek row** lao | Audience row dhoondhna |
| `db.query(...).delete()` | Shart se mel khaane wali rows **mitao** (commit par pakka) | Purane `scheduled` nudges hatana |
| `db.delete(row)` | Ek row mitao (commit par pakka) | Delete event / reminder |
| `db.close()` | Session band, connection wapas pool me | Har request ke end me (`get_db`) |

**Is setup ki do baatein:**
- `autocommit=False`: apne-aap kuch save nahi hota. `commit` likhna padta hai. Isliye "ya sab, ya kuch nahi" wala rule chalta hai.
- `autoflush=False`: query se pehle khud flush nahi hota. Isliye code me jagah-jagah `db.flush()` likha hai, jaise audience save karne ke baad, taaki nudge banate waqt naye students padhe ja sakein.

**Ek line me:** `add` = list me daalo → `flush` = DB ko dikhao (id lo), abhi pakka nahi → `commit` = pakka → koi error = `rollback`, sab saaf.
