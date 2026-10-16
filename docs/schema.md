# Schema — kaun si table, kaun sa column, aur kyun

Models `app/db/models/` me hain aur tables **Alembic migration** se banti hain —
kaise, wo [`../setup/migrations.md`](../setup/migrations.md) me hai.

---

## 1. Saat tables — kaun si aur kyun

| # | Table | Kya rakhti hai | Alag table kyun |
|---|---|---|---|
| 1 | `calendar_event` | TPO ka banaya event — type, title, date, time, mode, venue, status, cancel ka byora, kya badla | har cheez ka kendra; baaki tables isi se judti hain |
| 2 | `calendar_event_audience` | ek event ke liye ek row — opportunity type, courses, batches, departments | audience list hai (array), event row me thoosne par har query bhaari ho jaati; alag rehne se audience badalna bhi aasan |
| 3 | `calendar_event_recipient` | publish ke waqt freeze hui student list, `active` / `removed`, `seen_at` | audience **niyam** hai, recipient **nateeja**. Niyam baad me badle to bhi purane student ka record (aur uska "no longer applicable") bacha rehta hai. Read bhi tez — student ko apne event ek index se mil jaate hain |
| 4 | `calendar_reminder` | TPO aur student dono ke niji My Reminders | ye kisi audience ke nahi hote, na notification bhejte hain. Event table me daalte to har query me "ye niji to nahi?" wali shart lagani padti |
| 5 | `calendar_nudge` | kis student ko, kis cheez ka, kab nudge jaana hai; `scheduled / sent / skipped` | nudge ka apna jeevan hai — schedule, hold, skip, sent. Yahi row double-send rokti hai aur history bhi rakhti hai |
| 6 | `calendar_push_device` | mobile app ka push token + platform | token user ka hai, event ka nahi; logout par sirf yahi row hatti hai |
| 7 | `calendar_settings` | **poore platform ki ek hi row** — nudge timings, daily limit, quiet hours | ek hi row isliye ispar `org_id` nahi. Engine har tick par yahi padhta hai |

**Application Deadline ki koi table nahi.** Wo jobs service ki expiry date se
derive hoti hai — design ka pehla na-badalne-wala faisla. Isi liye job apply hote
hi deadline apne aap gayab ho jaati hai; kisi row ko mitana nahi padta.

`columns.py` **koi table nahi** — sirf wo column definitions jo baar-baar aati
hain (`primary_key()`, `required_id()`, `moment()`, `created_at()`, `text()`,
`flag()`, `count()`). Model file me ab sirf naam aur rule dikhta hai,
`Column(...)` ka dohraav nahi.

---

## 2. Ek asli example — ek event banne par kahan kya bana

Neeche sab kuch sach me chala kar liya gaya hai. TPO ne 18 Oct, 2:00 PM ka PPT
banaya (BTech · 2027 · Computer Science), aur student ne apna ek reminder jodа.

### Kadam 1 — TPO ne event banaya

```sql
select left(event_id::text,8) as event_id, event_type, title,
       event_date, start_at at time zone 'Asia/Kolkata' as start_ist,
       mode, venue, status
from calendar_event;
```

```
 event_id | event_type |             title             | event_date |      start_ist      |  mode   |        venue        |  status
----------+------------+-------------------------------+------------+---------------------+---------+---------------------+-----------
 13c8cbcb | ppt        | 47 billion Pre-Placement Talk | 2026-10-18 | 2026-10-18 14:00:00 | offline | Auditorium, Block A | published
```

> `event_date` alag column hai aur `start_at` alag — din timezone se nahi badalna
> chahiye, isliye date `Date` me, aur asli waqt UTC me (`at time zone` lagate hi
> wapas IST me 14:00 dikh gaya).

**`calendar_event_audience`** — audience ek hi row me, arrays ke saath:

```
 event_id | opportunity_type | courses | batches |     departments
----------+------------------+---------+---------+----------------------
 13c8cbcb | job              | {BTech} | {2027}  | {"Computer Science"}
```

**`calendar_event_recipient`** — us audience se nikle student, freeze hokar:

```
 event_id | student  | state  | seen_at
----------+----------+--------+---------
 13c8cbcb | 33333333 | active |
```

`seen_at` khali hai → student ke bell me ye notification abhi **unread** hai.

**`calendar_nudge`** — do nudge apne aap schedule ho gaye:

```
    nudge_type     | item_type |  status   |       kab_ist
-------------------+-----------+-----------+---------------------
 event_day_before  | event     | scheduled | 2026-10-17 14:00:00
 event_hour_before | event     | scheduled | 2026-10-18 13:00:00
```

### Kadam 2 — student ne apna reminder banaya

```
           title            | reminder_date | reminder_time | remind_before | owner_role
----------------------------+---------------+---------------+---------------+------------
 Revise DBMS before the PPT | 2026-10-18    | 12:00:00      | 1_hour        | student
```

Iska alert bhi `calendar_nudge` me chala gaya — ab teen rows:

```
    nudge_type     | item_type |  status   |       kab_ist
-------------------+-----------+-----------+---------------------
 event_day_before  | event     | scheduled | 2026-10-17 14:00:00
 reminder_alert    | reminder  | scheduled | 2026-10-18 11:00:00
 event_hour_before | event     | scheduled | 2026-10-18 13:00:00
```

> `item_type` isliye hai ki ek hi table teen tarah ke nudge rakhti hai — event ka,
> job deadline ka, aur apne reminder ka.

### Kadam 3 — TPO ne audience badal kar MBA kar diya

```
 event_id | student  |  state  | seen_at
----------+----------+---------+---------
 13c8cbcb | 33333333 | removed |
```

Row **delete nahi hui** — `state` `removed` ho gayi. Isi ek badlav se teen cheezein
apne aap ho gayin:

* student ke calendar par wo event ab **"No longer applicable"** (muted, struck) dikhta hai
* uske bell me reason ke saath notification gayi
* us event ke pending nudges hat gaye — bachi sirf uski apni reminder wali:

```
   nudge_type   |  status   | kyun
----------------+-----------+------
 reminder_alert | scheduled | -
```

Agar recipient ko delete kar dete, to na "no longer applicable" dikhta, na ye pata
chalta ki pehle kise bheja gaya tha.

### Khud chala kar dekhna ho

```bash
docker exec -it campus-calendar-db psql -U calendar -d campus_calendar

\dt                                  -- saari tables
select * from calendar_event;
select * from calendar_event_recipient;
select nudge_type, status, scheduled_at at time zone 'Asia/Kolkata' from calendar_nudge;
```

---

## 3. Teen baatein jo models me jaan-boojh kar hain

| Baat | Kyun |
|---|---|
| `student_id`, `company_id`, job ids par **FK nahi** | wo rows hamare DB me hain hi nahi — SkillsBridge ki hain |
| `event_date` `Date` hai, `timestamp` nahi | all-day cheez ka din timezone se nahi badalna chahiye (design doc, Date aur time wala hissa) |
| `start_at` / `end_at` `DateTime(timezone=True)` | DB me UTC, render user ke timezone me |

## 4. Unique constraints — inhi se galti rukti hai

| Table | Constraint | Kya rokta hai |
|---|---|---|
| `calendar_event_recipient` | `(event_id, student_id)` | ek student ek event me do baar |
| `calendar_nudge` | `(student_id, nudge_type, item_id, scheduled_at)` | **double-send** |
| `calendar_event_audience` | `event_id` unique | ek event ke do audience |

## 5. Indexes

| Index | Kiske liye |
|---|---|
| `ix_calendar_event_org_date` | mahine ka calendar ek query me |
| `ix_calendar_event_org_status` | sirf published nikalna |
| `ix_calendar_recipient_student` | student ko apne event dikhana |
| `ix_calendar_nudge_due` | scheduler ko due nudges |
| `ix_calendar_reminder_owner_date` | My Reminders |

## 6. Banane ka command

```bash
cd calendar-backend
make db-up
```

```
database created: campus_calendar
schema is up to date
tables: calendar_event, calendar_event_audience, calendar_event_recipient,
        calendar_nudge, calendar_push_device, calendar_reminder, calendar_settings
settings row created
```

Ye do kaam karta hai:

1. **migration** chalata hai — khali DB par saari saat tables, purane DB par sirf
   jo missing hai
2. `calendar_settings` me **ek row** daalta hai, agar pehle se nahi hai

Dobara chalao to kuch nahi tootta.

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

---

## 7. `calendar_event` — har column kyun hai

File: `app/db/models/calendar_event.py`

Ye table **TPO ka banaya hua ek event** rakhti hai — PPT, company visit, online
assessment, training, orientation, practice test, deadline ya other. Application
Deadline ki rows yahan **nahi** aatin; wo jobs API se derive hoti hain.

```python
class CalendarEvent(Base):
    __tablename__ = "calendar_event"
    __table_args__ = (
        Index("ix_calendar_event_org_date", "org_id", "event_date"),
        Index("ix_calendar_event_org_status", "org_id", "status"),
    )

    event_id = columns.primary_key()
    org_id = columns.required_id(index=True)
    ...
```

### 24 column, 8 sawaal

| Sawaal | Columns |
|---|---|
| Ye row hai kiski | `event_id`, `org_id` |
| Hai kya | `event_type`, `title`, `company_id` |
| Kab hai | `event_date`, `start_at`, `end_at` |
| Kahan hai | `mode`, `venue`, `online_platform` |
| Kis job se juda hai | `linked_job_*` (4) |
| Aur kya likha hai | `description` |
| Zinda hai ya cancel | `status`, `cancel_*` (4) |
| Kiska hai | `created_by`, `created_at`, `updated_at` |

---

### Ye row hai kiski

| Column | Code | Kyun |
|---|---|---|
| `event_id` | `columns.primary_key()` | UUID, app me banta hai — DB se id maangne ki zaroorat nahi, isliye row DB me jaane se pehle hi uski id pata hoti hai |
| `org_id` | `columns.required_id(index=True)` | BRD kehta hai "all TPOs in a college see every event" (BRD, line 89) — college ka daayra kahin to rakhna padega. Har query ki pehli shart yahi hai, isliye index |

> `org_id` BRD me **field ki tarah** nahi hai — ye multi-tenancy ke liye hai.

### Hai kya

| Column | Code | Kyun |
|---|---|---|
| `event_type` | `text(40, nullable=False)` | BRD ke Event Types wale hisse me 9 type gine hain (BRD, line 230). Publish ke baad **badalta nahi** (BRD, line 201) |
| `title` | `text(120, nullable=False)` | Max 120 — BRD ka hi number (BRD, line 202) |
| `company_id` | `columns.optional_id()` | BRD ke Create Event wale hisse me Company optional hai, kyunki orientation/training kisi company se nahi jude hote (BRD, line 203) |

> `company_id` par **FK nahi** — wo row SkillsBridge ke DB me hai, hamare me nahi.
> Naam dikhana ho to API se aayega.

### Kab hai

| Column | Code | Kyun |
|---|---|---|
| `event_date` | `columns.day()` | `Date` hai, `timestamp` nahi — all-day cheez ka din timezone badalne par khisakna nahi chahiye (design doc, Date aur time wala hissa) |
| `start_at` | `columns.moment()` | Deadline aur My Reminder par time hota hi nahi, isliye nullable (BRD, line 205) |
| `end_at` | `columns.moment()` | Start se baad me hona chahiye — ye rule Pydantic me lagega, DB me nahi (BRD, line 206) |

### Kahan hai

| Column | Code | Kyun |
|---|---|---|
| `mode` | `text(20)` | Offline / Online. Deadline, Online Assessment aur My Reminder par poochha hi nahi jaata, isliye nullable (BRD, line 207) |
| `venue` | `text(200)` | Mode = Offline par required, max 200 (BRD, line 208) |
| `online_platform` | `text(200)` | Mode = Online par required — sirf naam, **meeting link nahi** (BRD, line 209) |

> "required" dono ke liye **condition** par hai, isliye DB me dono nullable hain.
> Ye shart Pydantic validator me lagegi (design doc, Validation rules wala hissa).

### Aur kya likha hai

| Column | Code | Kyun |
|---|---|---|
| `description` | `columns.long_text()` | Rich text, optional, max 1000 (BRD, line 211). `Text` isliye kyunki rich text ka HTML 1000 visible characters se bada ho sakta hai — limit Pydantic me lagegi |

### Kis job se juda hai

| Column | Code | Kyun |
|---|---|---|
| `linked_job_kind` | `text(20)` | `campus` / `external` / null — picker me do option hain (UI spec, line 360) |
| `linked_job_id` | `columns.optional_id()` | `campus` par — SkillsBridge ka job id, **FK nahi** |
| `linked_job_url` | `text(2048)` | `external` par — `https://` se shuru (UI spec, line 387) |
| `linked_job_title` | `text(200)` | `external` par required, kyunki bahar ke link ka title hamare paas nahi hota (UI spec, line 392) |

> Ye 4 column **BRD me nahi** hain — UI spec me jude hain, wahan `<-- NEW` likha
> hai (UI spec, line 326). Rakhne ka faisla ho chuka hai: job link chahiye.

### Zinda hai ya cancel

| Column | Code | Kyun |
|---|---|---|
| `status` | `text(20, nullable=False, default="published")` | `published` / `cancelled`. Row **delete nahi hoti** — "published events can never be permanently deleted" (BRD, line 331) |
| `cancel_reason` | `text(40)` | Postponed / Company Withdrew / Created by Mistake / Other — mandatory hai, par sirf cancel karte waqt (BRD, line 320) |
| `cancel_note` | `text(200)` | Other chunne par "short explanation, max 200" (BRD, line 320) |
| `cancelled_by` | `columns.optional_id()` | Detail panel me "Cancelled by [Name] · [Date]" dikhana hai (BRD, line 357) |
| `cancelled_at` | `columns.moment()` | Usi line ka date |

> `cancel_reason` = `created_by_mistake` hone par event student ke calendar se
> hat jaata hai, par TPO ko dikhta rehta hai (BRD, line 325 se 328) — isliye bhi row
> delete nahi ki ja sakti.

### Kiska hai

| Column | Code | Kyun |
|---|---|---|
| `created_by` | `columns.required_id()` | **Sabse zaroori column** — "only the TPO who created an event can edit or cancel it" (BRD, line 89 aur 286). Har edit/cancel route isi se guzrega |
| `created_at` | `columns.created_at()` | `server_default=func.now()` — DB ka apna time, app ka nahi |
| `updated_at` | `columns.updated_at()` | `onupdate=func.now()` — detail panel me "last updated" (BRD, line 355) |

---

## Do index — kis query ke liye

| Index | Query | Kahan chalegi |
|---|---|---|
| `ix_calendar_event_org_date` | `where org_id = ? and event_date between ? and ?` | mahine/hafte ka calendar — sabse zyada chalne wali query |
| `ix_calendar_event_org_status` | `where org_id = ? and status = 'published'` | student ko sirf published dikhane ke liye |

Dono me `org_id` pehle hai, kyunki har query usi se shuru hoti hai.

## Jo is table me jaan-boojh kar **nahi** hai

| Cheez | Kahan hai | Kyun |
|---|---|---|
| Audience (courses, batches, departments) | `calendar_event_audience` | Ek event ka ek hi row, aur teeno ARRAY hain — event row har baar bhaari ho jaati |
| Kis-kis student ko bheja | `calendar_event_recipient` | Publish par list freeze hoti hai; `removed` state hi "No longer applicable" dikhane ka zariya hai |
| My Reminder | `calendar_reminder` | BRD me ye event type hai (BRD, line 240), par iska audience, mode, venue kuch nahi hota (BRD, line 343) — isliye alag table |
| All-day hai ya nahi | `event_type` | Drawer me "All day" ka koi option hai hi nahi — TPO sirf type chunta hai, aur sirf `Deadline` par time poochha nahi jaata. Alag column rakhte to wo `event_type` ko dekh kar hi bharna padta, aur ek jagah bhool jaane par row jhooth bolne lagti |
| "X students notified" ka number | `calendar_event_recipient` | Us event ki recipient rows gin lo — alag column rakhne par wo count aur asli list alag ho sakte the |
| Application Deadline | kahin nahi | Jobs API ki expiry date se derive hoti hai — design ka pehla na-badalne-wala faisla |
| Max length ke rules (120, 200, 1000) | Pydantic models | DB me `String(n)` bas upar ki chhat hai; asli error message Pydantic deta hai |

## Type kyun chuna — har faisla

Column ka naam BRD se aata hai, par **type kaunsa lagega** ye faisla hamara hai.
Har faisle ke peeche ek wajah hai:

| Faisla | Kahan | Kyun yahi |
|---|---|---|
| `UUID`, `Integer` nahi | har id | id app me banti hai, DB ke `nextval` se nahi — isliye row DB me jaane se pehle hi uski id haath me hoti hai. Doosri service ko id bhejni ho to bhi guess nahi ki ja sakti |
| `Date`, `DateTime` nahi | `event_date` | 2 October ka event har timezone me 2 October hi hona chahiye. `timestamp` rakhte to render karte waqt din khisak sakta tha (design doc, Date aur time wala hissa) |
| `DateTime(timezone=True)` | `start_at`, `end_at`, `cancelled_at`, `created_at`, `updated_at` | DB me UTC, render user ke timezone me. `timezone=True` ke bina Postgres `timestamp without time zone` banata hai aur offset chup-chaap gir jaata hai |
| `Text`, `String(1000)` nahi | `description` | Rich text editor HTML bhejta hai — 1000 **dikhne wale** character ka HTML 1000 se kaafi bada hota hai. Limit Pydantic me lagegi, DB me nahi |
| `String(2048)` | `linked_job_url` | Browser ka URL limit yahi maana jaata hai |
| `String(n)` chhoti jagah | `title(120)`, `venue(200)`, `cancel_note(200)` | Ye numbers BRD ke hain. DB me bhi lagane se aakhri raksha mil jaati hai — koi script Pydantic ke bina likhe to bhi 500 character ka title andar nahi ja sakta |
| `String(20)` / `String(40)` enum ke liye | `status`, `mode`, `event_type`, `cancel_reason` | Postgres `ENUM` jaan-boojh kar nahi — naya event type aane par `ALTER TYPE` chalana padta, aur ye list abhi badalti rahegi. Values ki jaanch Pydantic me hogi |
| `nullable=False` sirf 6 jagah | `org_id`, `event_type`, `title`, `event_date`, `status`, `created_by` | Ye wahi hain jo **har** event type me bharte hain. Baaki sab kisi na kisi type par khaali rehte hain (Deadline par time nahi, Online Assessment par venue nahi), isliye un par `nullable=False` lagta hi nahi |
| `default=` (Python side), `server_default=` nahi | `status` | Value app me set hoti hai, isliye object banate hi `event.status` padha ja sakta hai — DB se wapas padhne ka intezaar nahi karna padta |
| `server_default=func.now()` | `created_at`, `updated_at` | Time DB ka hona chahiye, app server ka nahi — do server alag timezone ya thoda aage-peeche chal rahe ho to bhi row ka time ek hi ghadi se aaye |
| `onupdate=func.now()` | `updated_at` | Har `UPDATE` par apne aap badle — koi route ise set karna bhool nahi sakta |
| Index sirf 3 jagah | `org_id` + do composite | Index har `INSERT` ko thoda mehenga karta hai, isliye sirf unhi par jo query me **har baar** aate hain |
| `columns.*` helper, seedha `Column(...)` nahi | poori file | `Column(UUID(as_uuid=True), nullable=False, index=True)` 7 jagah likha tha. Ab ek jagah likha hai — padhte waqt aankh `org_id = required_id(index=True)` par type nahi, **matlab** padhti hai |

> Helper **function** hai, constant nahi — SQLAlchemy ka ek `Column` object do
> table me share nahi ho sakta, isliye har call naya Column banata hai.

## Source

| Kya | Kahan |
|---|---|
| Field list, cancel reasons, permissions | `calendar-frontend/docs/requirements/campus-calendar-brd.md` |
| Linked Job picker | `calendar-frontend/docs/requirements/campus-calendar-ui-spec.md` |
| Table definition | `campus-calendar-backend-design.md`, Tables wala hissa |

---

## 8. `columns.py` — dohraav hatane wale helpers

File: `app/db/models/columns.py`

Isme **koi table nahi** hai. Sirf wo column definitions hain jo chhe models me
baar-baar aa rahi thin. Pehle aisa tha:

```python
org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
```

Ye exact line 7 jagah likhi thi. Ab:

```python
org_id = columns.required_id(index=True)
```

Padhne wale ko ab `UUID(as_uuid=True)` nahi, **matlab** dikhta hai — "ye id hai,
khaali nahi ho sakti, aur ispar query chalegi."

## Ek niyam jo tod nahi sakte

Har helper **function** hai, constant nahi:

```python
def primary_key() -> Column:
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

`PRIMARY_KEY = Column(...)` likh kar share nahi kar sakte — SQLAlchemy ka ek
`Column` object sirf **ek** table ka ho sakta hai. Doosri table me wahi object
lagaoge to pehli table se chhin jaayega. Isliye har call naya Column banata hai.

---

### 16 helper — kaunsa kahan

### Id ke liye — 4

| Helper | Deta hai | Kitni jagah | Kahan |
|---|---|---|---|
| `primary_key()` | `UUID, primary_key, default=uuid4` | 6 | har table ki apni id |
| `required_id(index=False)` | `UUID, nullable=False` | 9 | `org_id`, `student_id`, `owner_id`, `created_by`, `item_id` |
| `optional_id()` | `UUID, nullable=True` | 5 | `company_id`, `linked_job_id`, `cancelled_by`, `linked_id`, `updated_by` |
| `event_id(unique, index)` | FK → `calendar_event`, `ondelete=CASCADE` | 2 | `event_audience.event_id` (unique), `event_recipient.event_id` (index) |

**Kyun teen alag helper, ek nahi:** `required_id` aur `optional_id` ka farq
sirf `nullable` ka nahi hai — wo batate hain ki **row bina iske ban sakti hai ya
nahi**. `event_id` isliye alag hai kyunki wahi ek id hai jispar **FK lagti hai**
— baaki saari ids doosri service ki hain, hamare DB me unki row hai hi nahi.

> `required_id(index=True)` sirf wahan jahan query **har baar** us column se
> shuru hoti hai. Index har `INSERT` thoda mehenga karta hai, isliye har id par
> nahi lagaya.

### Text ke liye — 4

| Helper | Deta hai | Kitni jagah | Kahan |
|---|---|---|---|
| `text(length, nullable, default)` | `String(length)` | 23 | `title`, `venue`, `status`, `mode`, `note`, `*_reason` — sabse zyada use hone wala |
| `long_text()` | `Text, nullable=True` | 1 | `event.description` |
| `text_list()` | `ARRAY(String)` | 2 | `audience.courses`, `audience.departments` |
| `number_list()` | `ARRAY(Integer)` | 1 | `audience.batches` (passing years) |

**`text()` me length pehla argument kyun:** kyunki har baar wahi badalta hai.
`columns.text(120, nullable=False)` ek nazar me padha jaata hai — "120 ka text,
khaali nahi."

**`long_text()` alag kyun:** `description` rich text editor se aata hai. 1000
*dikhne wale* character ka HTML 1000 se kaafi bada hota hai, isliye uspar
`String(n)` ki chhat nahi lagayi — limit Pydantic me lagegi.

### Date aur time ke liye — 5

| Helper | Deta hai | Kitni jagah | Kahan |
|---|---|---|---|
| `day(nullable=False)` | `Date` | 2 | `event.event_date`, `reminder.reminder_date` |
| `clock(nullable=True)` | `Time` | 3 | `reminder.reminder_time`, `settings.quiet_hours_start/end` |
| `moment(nullable, index)` | `DateTime(timezone=True)` | 7 | `start_at`, `end_at`, `cancelled_at`, `seen_at`, `sent_at`, `alert_at`, `scheduled_at` |
| `created_at()` | `server_default=func.now()` | 3 | `event`, `event_recipient`, `reminder` |
| `updated_at()` | `server_default` + `onupdate` | 3 | `event`, `reminder`, `settings` |

**Teen alag naam — `day`, `clock`, `moment` — jaan-boojh kar:** design doc ka Date aur time wala hissa kehta
hai ki teen tarah ka time hai aur teeno ka treatment alag hai.

| Helper | Kya rakhta hai | Timezone ka asar |
|---|---|---|
| `day()` | sirf din | **koi nahi** — 2 October har jagah 2 October |
| `clock()` | sirf ghadi ka waqt | koi nahi — quiet hours 10 PM matlab har college me 10 PM |
| `moment()` | asli instant | DB me UTC, dikhte waqt user ke timezone me |

Agar teeno jagah `DateTime` laga dete, to `event_date` timezone badalne par ek
din aage-peeche khisak jaata.

**`created_at` / `updated_at` alag kyun, `moment(nullable=False)` kyun nahi:**
inki value **DB khud bharta hai** (`func.now()`), app nahi. `updated_at` me
`onupdate` bhi hai, matlab har `UPDATE` par apne aap badlega — koi route ise set
karna bhool nahi sakta.

### Baaki — 2

| Helper | Deta hai | Kitni jagah | Kahan |
|---|---|---|---|
| `flag(default=False)` | `Boolean, nullable=False` | 1 | `settings.deadline_reminder_same_day` |
| `count(default=0)` | `Integer, nullable=False` | 4 | `settings` ke chaaron number |

**`flag` aur `count` par `nullable=True` ka option nahi diya:** haan/naa ka
teesra jawab nahi hota, aur ginti ka khaali hona 0 se alag kuch nahi kehta. Jo
column null ho hi nahi sakta, uspar option dena baad me galti banwata hai.

---

## Jo helper **nahi** banaya

| Cheez | Kyun nahi |
|---|---|
| `enum()` | Postgres `ENUM` nahi use kar rahe — naya event type aane par `ALTER TYPE` chalana padta. Values ki jaanch Pydantic me hogi, isliye `text(20)` hi kaafi hai |
| `TimestampMixin` class | Mixin se `created_at`/`updated_at` chhup jaate hain. Chhe me se teen hi tables me dono hain, aur model padhte waqt saari columns ek hi jagah dikhni chahiye |
| `org_id()` naam ka apna helper | `required_id(index=True)` se zyada kuch nahi karta, aur ek aur naam yaad rakhna padta |

---

## Naya column jodte waqt

1. Helper se kaam ban raha hai → wahi lagao
2. Nahi ban raha → seedha `Column(...)` likh do, galat nahi hai
3. Wahi cheez **teesri** baar likhni padi → tab `columns.py` me helper banao

Helper tabhi banta hai jab dohraav sach me ho. Ek-do jagah ke liye naya naam
yaad rakhna padhna mehenga padta hai.
