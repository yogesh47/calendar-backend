# `columns.py` — har helper kahan aur kyun

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

## 16 helper — kaunsa kahan

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
| `flag(default=False)` | `Boolean, nullable=False` | 2 | `event.is_all_day`, `settings.deadline_reminder_same_day` |
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
