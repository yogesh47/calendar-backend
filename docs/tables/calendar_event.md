# `calendar_event` — har column kyun hai

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

## 24 column, 8 sawaal

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

## 1. Ye row hai kiski

| Column | Code | Kyun |
|---|---|---|
| `event_id` | `columns.primary_key()` | UUID, app me banta hai — DB se id maangne ki zaroorat nahi, isliye row DB me jaane se pehle hi uski id pata hoti hai |
| `org_id` | `columns.required_id(index=True)` | BRD kehta hai "all TPOs in a college see every event" (BRD, line 89) — college ka daayra kahin to rakhna padega. Har query ki pehli shart yahi hai, isliye index |

> `org_id` BRD me **field ki tarah** nahi hai — ye multi-tenancy ke liye hai.

## 2. Hai kya

| Column | Code | Kyun |
|---|---|---|
| `event_type` | `text(40, nullable=False)` | BRD ke Event Types wale hisse me 9 type gine hain (BRD, line 230). Publish ke baad **badalta nahi** (BRD, line 201) |
| `title` | `text(120, nullable=False)` | Max 120 — BRD ka hi number (BRD, line 202) |
| `company_id` | `columns.optional_id()` | BRD ke Create Event wale hisse me Company optional hai, kyunki orientation/training kisi company se nahi jude hote (BRD, line 203) |

> `company_id` par **FK nahi** — wo row SkillsBridge ke DB me hai, hamare me nahi.
> Naam dikhana ho to API se aayega.

## 3. Kab hai

| Column | Code | Kyun |
|---|---|---|
| `event_date` | `columns.day()` | `Date` hai, `timestamp` nahi — all-day cheez ka din timezone badalne par khisakna nahi chahiye (design doc, Date aur time wala hissa) |
| `start_at` | `columns.moment()` | Deadline aur My Reminder par time hota hi nahi, isliye nullable (BRD, line 205) |
| `end_at` | `columns.moment()` | Start se baad me hona chahiye — ye rule Pydantic me lagega, DB me nahi (BRD, line 206) |

## 4. Kahan hai

| Column | Code | Kyun |
|---|---|---|
| `mode` | `text(20)` | Offline / Online. Deadline, Online Assessment aur My Reminder par poochha hi nahi jaata, isliye nullable (BRD, line 207) |
| `venue` | `text(200)` | Mode = Offline par required, max 200 (BRD, line 208) |
| `online_platform` | `text(200)` | Mode = Online par required — sirf naam, **meeting link nahi** (BRD, line 209) |

> "required" dono ke liye **condition** par hai, isliye DB me dono nullable hain.
> Ye shart Pydantic validator me lagegi (design doc, Validation rules wala hissa).

## 5. Aur kya likha hai

| Column | Code | Kyun |
|---|---|---|
| `description` | `columns.long_text()` | Rich text, optional, max 1000 (BRD, line 211). `Text` isliye kyunki rich text ka HTML 1000 visible characters se bada ho sakta hai — limit Pydantic me lagegi |

## 6. Kis job se juda hai

| Column | Code | Kyun |
|---|---|---|
| `linked_job_kind` | `text(20)` | `campus` / `external` / null — picker me do option hain (UI spec, line 360) |
| `linked_job_id` | `columns.optional_id()` | `campus` par — SkillsBridge ka job id, **FK nahi** |
| `linked_job_url` | `text(2048)` | `external` par — `https://` se shuru (UI spec, line 387) |
| `linked_job_title` | `text(200)` | `external` par required, kyunki bahar ke link ka title hamare paas nahi hota (UI spec, line 392) |

> Ye 4 column **BRD me nahi** hain — UI spec me jude hain, wahan `<-- NEW` likha
> hai (UI spec, line 326). Rakhne ka faisla ho chuka hai: job link chahiye.

## 7. Zinda hai ya cancel

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

## 8. Kiska hai

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
