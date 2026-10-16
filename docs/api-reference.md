# API reference — kaunsi API kis cheez ke liye hai

Base URL: **`http://127.0.0.1:8001`** · Swagger: `http://127.0.0.1:8001/docs`

Ek hi API web aur mobile dono ke liye hai — koi alag `/mobile/...` nahi.
Har request me `Authorization: Bearer <token>` chahiye (sirf `/health` aur
`/auth/login` khule hain).

| Role | Kis API tak pahunch |
|---|---|
| `tpo` | `/calendar/*` (events, reminders, notifications, push, stream) |
| `student` | wahi `/calendar/*`, par event banana sirf `my_reminder` ka |
| `super_admin` | sirf `/settings` — `/calendar/*` par **403** |

Dates `YYYY-MM-DD`, times `HH:MM` **IST** me bhejte-lete hain; DB andar UTC rakhta hai.

---

## 1. Health aur login

### `GET /health`
API aur DB zinda hain ya nahi. Token nahi chahiye.
```json
{ "status": "ok", "database": "up" }
```

### `POST /auth/login`
Email + password se JWT. **Har client yahin se shuru karta hai.**
```json
// body
{ "email": "tpo@campus.test", "password": "tpo@1234" }
// 200
{ "access_token": "eyJ…", "token_type": "bearer", "expires_in": 43200,
  "user": { "user_id": "…", "org_id": "…", "name": "Priya Sharma", "email": "…", "role": "tpo" } }
```
Galat password → **401** `{"detail": "Email or password is incorrect"}`.

### `GET /auth/me`
Token kiska hai — app ke restart par session check karne ke liye.

---

## 2. Calendar padhna

### `GET /calendar/events`
**Calendar screen ka main data.** Ek hi list me teen cheezein aati hain:

| `event_type` | Kya hai | Kaun dekhta hai |
|---|---|---|
| `ppt`, `company_visit`, `online_assessment`, `training`, `orientation`, `practice_test`, `deadline`, `other` | TPO ke banaye events | TPO: college ke saare · Student: sirf apne audience wale |
| `my_reminder` | niji reminder | sirf banane wala |
| `nudge` | system ka bheja hua reminder | sirf wo student/TPO |
| `deadline` (id `deadline-<job_id>`) | campus job ki last date, `app/services/jobs.py` se | TPO: saari · Student: apne department wali |

Query (dono optional, mobile month view ke liye):

| Param | Matlab |
|---|---|
| `from_date` | is date se pehle khatam hone wale items chhod do |
| `to_date` | is date ke baad shuru hone wale items chhod do |

```bash
curl "$API/calendar/events?from_date=2026-10-01&to_date=2026-10-31" -H "Authorization: Bearer $TOKEN"
```

Har item me kaam ke field: `event_id`, `event_type`, `title`, `company`,
`event_date`, `end_date`, `start_time`, `end_time`, `mode`, `venue`,
`online_platform`, `description`, `note`, `status`, `cancel_reason`,
`cancel_note`, `cancelled_at`, `created_by_name`, `notified_count`, `audience`,
`linked_job`, `linked_type`, `linked_id`, `is_owner`, **`applies_to_me`**,
**`removed_reason`**.

> `applies_to_me: false` ka matlab — student ko audience se hata diya gaya;
> item muted/struck "No longer applicable" dikhana hai (FR-CAL-17).

### `GET /calendar/coming-up?limit=3`
**Dashboard ka "Coming Up" card.** Aaj se aage ke agle N items, date+time se
sorted; cancelled, no-longer-applicable aur nudges ismein nahi aate.

### `GET /calendar/stream`
**SSE** — kuch bhi badla to turant pata chal jaaye (doosri screen par bana event,
bheja gaya nudge, wagairah). Token header me nahi, **query me** jaata hai:
```
GET /calendar/stream?token=<jwt>
event: calendar
data: <event_id | "nudges" | "delete-all">
```
Client ko bas `fetchEvents()` dobara chala dena hai. Har 20 second par
`: keep-alive` aata rehta hai.

---

## 3. Event banana / badalna (TPO)

### `POST /calendar/events` → **201**
Ek hi API se **har type** banta hai — event bhi, reminder bhi.
`event_type: "my_reminder"` ho to student bhi bula sakta hai; baaki har type par
student ko **403** milta hai.

```json
{ "event_type": "ppt", "title": "Pre-Placement Talk", "company": "47 billion",
  "event_date": "2026-10-22", "end_date": "2026-10-22",
  "start_time": "10:00", "end_time": "11:30",
  "mode": "offline", "venue": "Auditorium, Block A",
  "description": "<p>Bring your resume</p>",
  "audience": { "opportunity_type": "job", "courses": ["BTech"],
                "batches": [2027], "departments": ["Computer Science"] },
  "remind_before": "none", "linked_type": null, "linked_id": null,
  "linked_job": { "kind": "campus", "campus_job": "47 billion — SDE", "url": null, "title": null } }
```

Peeche kya hota hai: audience row banti hai → matching students ki recipient rows
→ unke nudges schedule hote hain → SSE push. Pura silsila
[`flows/create-event.md`](flows/create-event.md) me hai.

Validation fail → **422** aur hamesha ek line ka message:
`{"detail": "Venue is required for an offline event"}`.

### `PUT /calendar/events/{event_id}`
Event ya apna reminder badalna. Body `POST` jaisi hi.
Dusre TPO ka event → **403**, dusre ka reminder → **403**, mila hi nahi → **404**.
Pending nudges nayi date par dobara schedule ho jaate hain.

### `POST /calendar/events/{event_id}/cancel`
```json
{ "reason": "postponed | company_withdrew | created_by_mistake | other", "note": "optional, 200 char" }
```
Event calendar par rehta hai — muted + struck + "Cancelled". `other` par note
zaroori. Students ko notification jaati hai; `created_by_mistake` par unke
calendar se item **hat** jaata hai aur message hota hai "Please ignore the earlier
notification about …". Aane wale nudges cancel ho jaate hain.

### `POST /calendar/audience/count`
Publish se pehle "kitne students notify honge" — sirf ginti deta hai, kuch banata
nahi.
```json
{ "audience": { "opportunity_type": "job", "courses": ["BTech"], "batches": [2027], "departments": ["Computer Science"] } }
→ { "count": 38 }
```

---

## 4. Delete (soch kar)

| API | Kya karta hai |
|---|---|
| `DELETE /calendar/events/{id}` → **204** | apna reminder, ya apna banaya event hamesha ke liye hata deta hai (uske nudges bhi) |
| `POST /calendar/events/bulk-delete` | `{ "event_ids": [...] }` → `{ deleted, skipped, count }` — jo apne nahi wo `skipped` me |
| `DELETE /calendar/events?confirm=yes` | dev wala "Delete all": org ke saare events + **apne** reminders. `confirm=yes` na ho to **400** |

> `delete all` doosre user ke niji reminders ko haath nahi lagata.

---

## 5. Notifications aur nudges

### `GET /calendar/notifications`
Bell panel ka data — TPO/student ke apne liye. Event wali notifications aur bheje
hue nudges, dono ek hi list me, naye sabse upar.

```json
[{ "notification_id": "…", "event_id": "…", "message": "New event: Pre-Placement Talk on 22 Oct, 10:00. Check your Campus Calendar.",
   "created_at": "2026-10-16T08:11:00Z", "is_read": false, "kind": "new_event" }]
```

`kind` se UI label/CTA decide hota hai:

| `kind` | Kab aata hai | Feed card |
|---|---|---|
| `new_event` | naya event mila | New Event · View on Calendar |
| `event_updated` | event badla | Event Updated · View on Calendar |
| `event_cancelled` | cancel hua | Event Cancelled |
| `not_applicable` | audience se hataya gaya | No Longer Applicable |
| `ignore_earlier` | created-by-mistake | koi card nahi |
| `event_day_before` / `event_hour_before` | N-S1 nudge | Event Tomorrow / In 1 Hour |
| `assessment_day` | N-S3 nudge | Online Test Today |
| `deadline_days_before` / `deadline_last_day` | N-S2 nudge | Applications Closing / Last Day |
| `reminder_alert` | apne reminder ka alert | — |

### `GET /calendar/notifications/unread-count`
`{ "unread": 3 }` — mobile ke calendar icon ka **red dot** aur header ka badge.

### `POST /calendar/notifications/{notification_id}/read` → **204**
Ek notification padhi gayi (tap par).

### `POST /calendar/notifications/read-all` → **204**
"Mark all as read".

> Nudges kab bante aur kab jaate hain — [`flows/nudges.md`](flows/nudges.md).

### `POST /calendar/jobs/{job_id}/apply` → **201** · `DELETE` → **204**
Demo apply / withdraw (sirf `student`). Apply karte hi us job ki deadline student
ke calendar se hat jaati hai aur uske **pending deadline nudges** bhi — BRD
FR-CAL-08 / FR-CAL-26 yahi kehte hain.

### Jobs service se kya-kya chahiye

Abhi jobs `app/services/jobs.py` me hardcoded hain. Asli 7Seers Jobs API aate hi
sirf wahi file badlegi — `from_payload()` adapter pehle se wahi shape padhta hai
jo aapke job-detail response me aata hai:

| Calendar ko chahiye | Jobs payload me |
|---|---|
| job id | `job_description.job_id` |
| title / company | `job_description.job_title` · `company_info.name` |
| deadline ki date | `job_description.application_end_date` |
| job chalu hai? | `job_description.status == "active"` |
| kis department ke liye | `department: [...]` (case kuch bhi ho, match case-insensitive hai) |
| kis batch ke liye | `job_description.batch` (`null` = sab batch) |
| student eligible hai? | `job_description.is_eligible` |
| apply kar chuka? | `application_status` (null/khali = nahi kiya) |

---

## 6. Push (mobile)

### `POST /calendar/push/devices` → **201**
App apna push token yahan register karta hai. Wahi token dobara bhejo to wahi row
update hoti hai (duplicate nahi banti).
```json
{ "token": "expo-push-token-abc123", "platform": "android | ios | web" }
→ { "device_id": "…", "platform": "android", "created_at": "…" }
```

### `DELETE /calendar/push/devices/{token}` → **204**
Logout par token hata do.

> Abhi koi FCM/APNs provider juda nahi hai — backend token rakhta hai aur engine
> jaanta hai kab bhejna hai; asli push nikalne ki ek line
> `app/jobs/nudge_runner.py` me aayegi.

---

## 7. Super Admin settings

### `GET /settings` · `PUT /settings`
Poore platform ki ek hi row (FR-CAL-27). Sirf `super_admin`; TPO/student ko **403**.

```json
{ "event_reminder_days_before": 1,      // 1–30
  "event_reminder_hours_before": 1,     // 1–12
  "deadline_reminder_days_before": 2,   // 1–30
  "deadline_reminder_same_day": true,
  "daily_nudge_limit": 3,               // 1–10
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "07:00" }
```
Range se bahar → **422** `{"detail": "Event Reminder: days before must be 30 or less"}`.
Nudge engine har tick par yahi row padhta hai; pehle se schedule nudges nahi badalte.

---

## 8. Status codes ek nazar me

| Code | Kab |
|---|---|
| 200 / 201 / 204 | theek · bana · bina content ke ho gaya |
| **400** | `?confirm=yes` ke bina delete-all |
| **401** | token nahi / expire ho gaya |
| **403** | galat role (student event banaye, TPO settings khole, doosre ka event edit/cancel/delete) |
| **404** | event ya reminder mila hi nahi |
| **422** | body galat — `detail` me hamesha **ek line** ka seedha message |
| **500** | `{"detail": "The server could not complete that request. Please try again."}` |

Error ka wording `app/errors.py` banata hai, isliye frontend seedha `detail`
uthakar toast me dikha deta hai.

---

## 9. Jaldi test karne ke liye

```bash
API=http://127.0.0.1:8001
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"tpo@campus.test","password":"tpo@1234"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s $API/calendar/events -H "Authorization: Bearer $TOKEN"
curl -s "$API/calendar/coming-up?limit=3" -H "Authorization: Bearer $TOKEN"
curl -s $API/calendar/notifications/unread-count -H "Authorization: Bearer $TOKEN"
```

Login aur DB ki details [`credentials.md`](credentials.md) me hain.
