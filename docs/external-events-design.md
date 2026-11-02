# External Events: design (backend + frontend)

Status: **proposal**, nothing built yet. Use cases: `calendar-frontend/docs/use-cases.md` §8–10 (UC-120 to UC-163).

An external event is something **no TPO created** that still belongs on a student's calendar. There are three kinds:

| Kind | Who creates it | Saved? | Example |
|---|---|---|---|
| **A. Linked** | The student, against a 7Seers item | Yes, one row | "Mock interview for TCS at 6 PM", "Finish SQL module 3" |
| **C. Outside** | The student, linked to nothing | Yes, one row (same table, no link) | Off-campus interview, hackathon, exam |
| **B. Auto** | The system, from the student's data | **No**: built on every read, like job deadlines (`deadlines.py`) | Hiring stage date, cohort assessment closing, course end date |

A and C are the same thing: a student's own event, where the link is optional. B is a read-only view of data that lives in another service, so it is computed and never copied.

---

## 1. What can be linked

| `linked_type` | Item | Id from (Student 2.0) | "Open" goes to |
|---|---|---|---|
| `job` | Campus job | `job_id` | `/jobs/:jobId` |
| `external_job` | Off-campus job | job id / url | the job's `apply_link` |
| `hiring_stage` | A stage of a job I applied to | `job_id` + `stage_name` | `/jobs/:jobId` |
| `learning_path` | Role / learning path | role id | `/learning-hub/roles/:id` |
| `course` | Course (optionally a module) | course id (+ module id) | `/learning-hub/courses/:id` |
| `cohort` | Cohort session / assignment | `cohortId` | `/learning-hub/cohorts/:id` |
| `mock_interview` | Mock for a job / practice card / cohort | `jobId` / `cardId` / `cohortId` | `/mock-interview/:jobId/setting-up`, `/practice/:cardId/...`, `/cohorts/:cohortId/...` |
| `assessment` | Skill / course / cohort / practice assessment | assessment id | the assessment page |
| `skill` | Skill goal | `skillId` | `/learning-hub/skills/:id` |
| `certificate` | Certificate to earn | `certId` | `/certificate/:certId` |
| *(none)* | Outside event | — | its own `url`, if any |

Ids in the main platform are not our UUIDs, so `linked_id` is **text**, not a UUID column.

---

## 2. Database

### 2a. New table `calendar_student_event` (kinds A and C)

This is a separate table, not part of `calendar_reminder`. A reminder is one moment with an alert. An external event has a start and an end, a category, a venue or link, and a done state.

| Column | Type | Notes |
|---|---|---|
| `student_event_id` | uuid PK | |
| `org_id`, `owner_id` | uuid | Only the owner ever sees it |
| `category` | text(20) | `interview` · `exam` · `hackathon` · `workshop` · `study` · `practice` · `personal` · `other` |
| `other_category` | text(80) | Required when `other`, as with `other_type` on events |
| `title` | text(120) | |
| `starts_at`, `ends_at` | timestamptz (UTC) | Plus `event_date`, `start_time`, `end_time` and `time_zone` (the student's zone), as reminders store them |
| `all_day` | bool | |
| `mode` | text(10) | `offline` / `online` / `''` |
| `venue`, `url` | text | `url` must be `https://` |
| `company` | text(120) | Free text (an off-campus company is not in our list) |
| `note` | text(500) | |
| `remind_before` | text(20) | Same values as My Reminder |
| `linked_type` | text(20), nullable | §1 |
| `linked_id` | text(64), nullable | |
| `linked_title`, `linked_url` | text | **Snapshot** taken at save time, so the calendar draws without calling other services |
| `linked_state` | text(20) | `open` · `done` · `expired` · `removed` (UC-133–135) |
| `done_at` | timestamptz | Set by the student or by a platform hook |
| `source` | text(20) | `calendar` · `login_popup` · `item_page` ("Add to calendar") · `import` |
| `series_id`, `recurrence` | | Repeat, as on events and reminders |
| `created_at`, `updated_at` | | |

Indexes:
- `(owner_id, starts_at)` for the month query
- `(linked_type, linked_id)` for hooks that update every event linked to one item

Migration: `setup/migrations/versions/<rev>_student_events.py`, then run `make db-up`.

### 2b. Changes to existing tables

| Table | Add |
|---|---|
| `calendar_settings` | `external_events_enabled` (bool, true) · `external_popup_enabled` (bool, true) · `external_popup_every_days` (int, 7) · `external_events_limit` (int, 50) · `auto_items_sources` (text, e.g. `hiring_stage,cohort,course`) |
| `calendar_user` | `popup_seen_at` (timestamptz) · `popup_never` (bool) |
| `calendar_nudge` | Nothing. Adds `nudge_type` values `external_alert` and `hiring_stage_*` / `cohort_*` / `course_*`, with `item_type = "student_event"` or `"auto"` |

---

## 3. Backend code

```
app/
  db/models/calendar_student_event.py        new table
  models/student_event_model.py              StudentEventIn / StudentEventOut (Pydantic)
  services/student_events.py                 create / update / delete / done, owner checks
  services/links/                            one small resolver per linked_type
      __init__.py                            registry: RESOLVERS = {"job": jobs, "course": courses, ...}
      jobs.py  courses.py  cohorts.py  mocks.py  assessments.py  roles.py
  services/auto_items.py                     kind B: hiring stages, cohort and course dates (like deadlines.py)
  routes/student_events.py                   the routes in §4
```

**Resolver contract.** One per type; each answers four questions:

```python
class LinkedItem(BaseModel):
    type: str; id: str; title: str; url: str
    state: Literal["open", "done", "expired", "removed"]
    dates: list[ItemDate] = []           # for kind B: (label, starts_at, ends_at)

def options(student, query) -> list[LinkedItem]   # what this student may link (picker)
def get(student, item_id) -> LinkedItem | None    # None = not theirs / not found → 422
def state(student, item_id) -> str                # live status for UC-133
def dates(student) -> list[ItemDate]              # kind B only
```

In this demo each resolver reads a hardcoded list, the way `jobs.py` does today. In the real product it calls the main 7Seers API (Jobs, Learning Hub) with the student's token. **The calendar never trusts an id from the browser:** `get()` checks that the item belongs to that student before saving.

**Rules in `student_events.py`:**
- Only the owner can read, edit or delete; anyone else gets 403. A TPO never sees these rows, not even in "Delete all".
- `linked_type` given → `linked_id` is required and `get()` must return the item. Otherwise 422 "Choose what this is linked to".
- The upcoming limit is `external_events_limit` → 422 "You've reached N upcoming events…".
- `external_events_enabled = false` → 403 on create. Existing rows are still shown.
- Saving schedules one `external_alert` nudge from `remind_before`. Like My Reminder, it does **not** count towards the daily limit and ignores quiet hours, because the student picked the time.
- Delete removes the row and its pending nudges; a series can be deleted with `?scope=series`.

---

## 4. API

| Method | Path | What |
|---|---|---|
| `GET` | `/calendar/events` | **Unchanged path.** For a student, it also returns their student events (`event_type: "external"`) and kind B items (`event_type: "auto"`, read-only) |
| `POST` | `/calendar/student-events` | Create (A or C) |
| `PUT` | `/calendar/student-events/{id}` | Edit |
| `DELETE` | `/calendar/student-events/{id}?scope=one\|series` | Delete |
| `POST` | `/calendar/student-events/{id}/done` | Mark done / undone |
| `GET` | `/calendar/link-options?type=course&q=sql` | Picker: items this student may link (from the resolver) |
| `GET` | `/calendar/prompt` | Login pop-up: `{ show: bool }` (settings on, not `popup_never`, `popup_seen_at` older than N days) |
| `POST` | `/calendar/prompt` | `{ action: "later" \| "never" }` |
| `POST` | `/calendar/hooks/activity` | **Service-to-service only** (service token, not a user JWT). Body: `{ student_id, type, id, event }`, e.g. `mock_completed`, `assessment_completed`, `applied`, `course_completed`, `job_closed`, `stage_scheduled` |
| `GET` / `PUT` | `/settings/calendar` | Plus the new settings in §2b |

**What the hook does:** it finds rows by `(linked_type, linked_id, owner)` and sets `linked_state`. On `mock_completed` it also sets `done_at`. It drops pending nudges that no longer apply, and calls `live_stream.publish()` so an open calendar refreshes straight away.

If the main platform cannot send hooks yet, there is a fallback: `GET /calendar/events` asks `state()` for linked rows in view and caches the result for 5 minutes.

---

## 5. Kind B (auto items)

`auto_items.py` works like `deadlines.py`: on every `GET /calendar/events` for a student it asks each enabled resolver for `dates(student)` and returns them as read-only items.

| Source | Item | Example title |
|---|---|---|
| `hiring_stage` | `hiring_stages[].scheduled_at` of jobs I applied to | "Infosys · Technical Round" |
| `cohort` | Cohort session / assessment window | "Cohort assessment closes" |
| `course` | Course end date | "SQL course ends" |
| `certificate` | `expires_at` | "SQL certificate expires" |

- Nothing is saved, so a date changed in Jobs or Learning Hub shows up on the next load.
- Nudges for these are created by the existing loop, the same way `schedule_deadlines()` creates them today. A new `schedule_auto_items()` is idempotent thanks to the unique key on `calendar_nudge`. These nudges **do** count towards the daily limit, and their priority sits next to Deadline.
- The student can hide a source (UC-148). That is a per-user list on `calendar_user`; it removes items from the read only.

---

## 6. Frontend

### Calendar package (`src/calendar`): small, generic change
- Add two item kinds, `external` and `auto`, each with its own colour in `CALENDAR_ITEM_STYLE` (proposal: teal for external, indigo outline for auto).
- Add both to `Legend`.
- No modal and no API code: the package still only draws items and passes on clicks.

### App (`src/modules/Calendar`)
| Piece | What |
|---|---|
| `components/StudentEventDialog` | One-step modal: category (+ Other name), title, date and time, **Linked to** (type → searchable item list from `/link-options`), mode / venue / link, company, note, remind before, repeat. Same frame as the other modals (`Modal`, `ModalHeader/Body/Footer`) |
| `EventDetailModal` config | For `external`: the linked item with its live state ("Course 60% done", "Mock completed ✓"), plus **Open** (the linked url), **Mark done**, **Edit** and **Delete**. For `auto`: read-only, with an **Open** button only |
| `components/LoginPrompt` | Shown once after a student logs in when `GET /prompt` says so. Buttons: "Add an event", "Later", "Don't ask again" |
| `pages/CalendarPage` | New `modal` kinds `studentEvent` and `prompt`; "+ Add Reminder" becomes a small menu: Reminder / Event |
| `services/api.ts` | `student-events`, `link-options` and `prompt` calls; maps `event_type: "external" / "auto"` |
| `services/addToCalendar.ts` | `requestAddToCalendar({ linkedType, linkedId, title, url, date? })`. It works like `requestOpenEvent`: any page can call it, and the Calendar page opens `StudentEventDialog` prefilled |

### Student portal (7Seers-Student-2.0)
- Add an **"Add to calendar"** button on the job detail, course, cohort, mock interview setup, assessment and certificate pages.
- The button calls `requestAddToCalendar(...)` with what the page already has: the id, title and route. No new API is needed on that side.

---

## 7. Build order

| Step | What | Use cases |
|---|---|---|
| 1 | Table + migration + CRUD + `external_alert` nudge + kind C only (no link) + dialog + style | UC-150, 153–158, 194 |
| 2 | Resolver registry + `link-options` + "Linked to" picker; start with `job`, `mock_interview`, `assessment` | UC-120, 121, 126, 127, 132 |
| 3 | "Add to calendar" buttons in Student 2.0 + `requestAddToCalendar` | UC-131 |
| 4 | Add `course`, `cohort`, `learning_path`, `skill`, `certificate` resolvers | UC-123–125, 128–130 |
| 5 | Activity hook (or fallback) → live state, auto done | UC-133–135 |
| 6 | Kind B `auto_items.py` + their nudges + hide by source | UC-140–148, 195, 196 |
| 7 | Login pop-up + Super Admin settings | UC-151, 152, 214–217 |
| 8 | Google / Outlook import, clash with campus events, share with TPO | UC-159–162 |

Steps 1–3 are enough for "a student can add an event for a job, a mock or an assessment and open it from the calendar".

---

## 8. Open questions for product

1. Does an external event count towards the same 50 limit as My Reminders, or have its own?
2. Can a TPO see **counts** only, e.g. "12 students have off-campus interviews this week" (UC-232)? Or nothing at all?
3. Kind B: which sources are on by default? (Proposal: hiring stages and cohorts.)
4. Login pop-up: how often? Every login, or once every 7 days?
5. When a linked job is deleted: keep the event with "Job removed" (proposal), or delete it?
