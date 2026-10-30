# Time zones — the full flow, step by step

Campus Calendar now works outside India too: America, Australia, Europe, Africa,
anywhere. This doc explains where a time zone comes from, where it is stored,
what to send to the API, and which clock each event, reminder, nudge and
notification runs on.

---

## 0. Quick reference — what each step needs

| Step | What the frontend sends | Required? | If it is not sent |
|---|---|---|---|
| **Creating a college (org)** | `time_zone` (e.g. `"Australia/Sydney"`) | No | `DEFAULT_ORG_TIMEZONE` (IST); the college's first staff sign-in sets it automatically |
| **Sign-up / creating a user** | `time_zone` = `Intl.DateTimeFormat().resolvedOptions().timeZone` | No | `null` → the college's zone is used until their first sign-in |
| **Login** | Only `email` + `password` — the zone is **not** part of the login body | — | — |
| **Right after login** (and every time the app opens) | `PUT /auth/me/time-zone` `{ "time_zone": "<browser zone>" }` | **Yes** (the frontend does it automatically) | Nudges and notifications keep using the old zone |
| **Creating / editing an event** | `event_date`, `start_time`, `end_time` **on the campus clock** + `time_zone` (= `org_time_zone`) | `time_zone` is optional | The backend uses the org zone — the date and time must then be on the org's clock |
| **Creating / editing a reminder** | Date and time **on the user's clock** + `time_zone` (= browser zone) | `time_zone` is optional | The backend uses the user's zone (else the org zone) |
| **Deadline / all-day item** | Only `event_date`, `start_time: null` | — | No conversion |
| **Reading events** | Nothing — the response carries `starts_at` / `ends_at` (UTC) + `time_zone` | — | — |
| **Changing the college's zone** (Super Admin) | `time_zone` in `PUT /settings` | No | The zone stays as it is |

### 0.1 At sign-up

> This calendar backend has **no sign-up API** yet — users are seeded from
> `setup/init_db.py`, and the main platform (TPO Portal) creates users. When a
> user or a college is created there, send these two things:

**When creating a user** (`calendar_user` row):

```json
{
  "user_id": "…",
  "org_id": "…",
  "name": "Rahul Verma",
  "email": "rahul@college.edu",
  "role": "student",
  "time_zone": "America/New_York"
}
```

- `time_zone` → from the browser filling in the sign-up form: `Intl.DateTimeFormat().resolvedOptions().timeZone`.
- If an admin creates the account for someone else (bulk import, invite), **do
  not send** `time_zone` (`null`). The admin's browser is not that student's
  zone; it is set automatically on the student's first sign-in.

**When creating a college** (`calendar_settings` row):

```json
{ "org_id": "…", "time_zone": "Australia/Sydney", "time_zone_source": "admin" }
```

- You know where the college is → `time_zone` + `time_zone_source: "admin"`.
- You don't → send nothing; it is copied from the template row (`source: "default"`)
  and the first TPO / Super Admin sign-in sets it (`source: "detected"`).

### 0.2 At login

1. `POST /auth/login` → `{ "email": "…", "password": "…" }` — no zone needed.
2. Compare the response's `user.time_zone` with the browser's zone.
3. If they differ (or it is `null`) → `PUT /auth/me/time-zone` `{ "time_zone": "<browser zone>" }`.
4. Save the returned `user` (new `time_zone` + `org_time_zone`) in the session.
5. Repeat steps 2–4 **every time the app opens** (after `GET /auth/me`) — so
   someone who travels to another country with their laptop is picked up too.

Details: section 3.

### 0.3 When creating / editing an event

1. Let the user fill the form in the browser's local time (they see their own time).
2. Pick the zone: new event → `session.user.org_time_zone`; edit → the event's own `time_zone`.
3. Local date + time → instant → date + `HH:mm` in that zone.
4. Send `event_date`, `end_date`, `start_time`, `end_time` (on that zone's clock) + `time_zone`.

```json
POST /calendar/events
{
  "event_type": "ppt",
  "title": "TCS Pre-Placement Talk",
  "event_date": "2026-10-28",
  "end_date": "2026-10-28",
  "start_time": "21:00",
  "end_time": "22:30",
  "time_zone": "Australia/Sydney"
}
```

Reminders work the same way, except the zone is the browser's. Details: section 4.

### 0.4 Existing users with no time zone (`time_zone = null`)

Every user created before this update has an empty (`null`) `calendar_user.time_zone`.
Nothing special is needed for them:

| When | What happens |
|---|---|
| Until they sign in | The **college's zone** is used everywhere: nudges (8 AM / 9 AM), quiet hours, the daily limit, notification text, new reminders. If the college is on IST, everything stays on IST as before. |
| First sign-in / app open | The browser sends its zone and `time_zone` is filled in. |
| They are in India | Nothing changes — nudges stay where they were. |
| They are abroad (e.g. New York) | Their pending "morning" nudges move to the New York morning (section 7.3). |

Existing events and reminders were filled with `Asia/Kolkata` by migration
`d4b2e6f8a031`, so their times did not move.

### 0.5 India: "Asia/Calcutta" vs "Asia/Kolkata"

Chrome in India reports the zone's **old name, `Asia/Calcutta`**. Both are the same
zone, but as different strings comparisons failed and the panel read "Calcutta time".
So the backend (`clock.canonical_zone`) and the frontend (`lib/timeZone.ts` → `canonicalZone`)
both turn old names into current ones: `Asia/Calcutta → Asia/Kolkata`,
`Asia/Saigon → Asia/Ho_Chi_Minh`, `Europe/Kiev → Europe/Kyiv`, and so on.
The database always gets the current name; migration `f6d4a8b0c253` renamed
old names already stored.

---

## 1. Three rules (everything rests on these)

| # | Rule | Meaning |
|---|---|---|
| 1 | **The screen always shows the viewer's own local time** | Someone in London sees London time, someone in New York sees New York time. The browser's zone is the screen's zone. |
| 2 | **The database always stores a UTC instant + the item's zone** | `start_at` / `end_at` in UTC, plus `time_zone` (the zone the time was entered in). |
| 3 | **Every item's zone belongs to its "owner"** | Event → the college (campus) zone. Reminder → its creator's zone. A nudge's "8 AM" → the student's zone. |

---

## 2. Three kinds of time zone

| Whose | Stored in | How it is set | Who can change it |
|---|---|---|---|
| **The college (org)** — campus time | `calendar_settings.time_zone` (one row per org, by `org_id`) | Automatically: the zone of the browser used for the college's **first staff sign-in** (TPO / Super Admin) | Only the Super Admin, from the Settings page |
| **The user** — where they are now | `calendar_user.time_zone` | Automatically: the browser's zone is sent **on every sign-in / app open** | Nobody manually — the browser reports it |
| **The item** — an event / reminder | `calendar_event.time_zone`, `calendar_reminder.time_zone` | At creation: event = college zone, reminder = user zone | It stays the same when the item is edited |

Many colleges can share one zone, and every college can be in a different zone —
each org has its own settings row, so both work.

### 2.1 Where the college zone came from

`calendar_settings.time_zone_source` records how the zone was set:

| Value | Meaning | Changes automatically? |
|---|---|---|
| `default` | Nobody has set it yet (`DEFAULT_ORG_TIMEZONE` from `.env`, default `Asia/Kolkata`) | **Yes** — on the first staff sign-in |
| `detected` | Taken from the browser of the first staff sign-in | No |
| `admin` | Chosen by the Super Admin in Settings | No |

So if the TPO of an Indian college travels to London and signs in from there,
**the college zone stays IST**. Only `default` is ever replaced automatically.

A student's sign-in **never** changes the college zone.

---

## 3. What happens at sign-in (step by step)

```
Browser                                   Backend
───────                                   ───────
1. POST /auth/login  ───────────────────▶ token + user
2. zone = Intl.DateTimeFormat()
          .resolvedOptions().timeZone      (e.g. "America/New_York")
3. if user.time_zone !== zone:
   PUT /auth/me/time-zone  ─────────────▶ a) calendar_user.time_zone = zone
       { "time_zone": zone }               b) the student's pending "morning" nudges
                                              move to the new zone (section 7.3)
                                           c) TPO / Super Admin + org source "default"
                                              → org zone = zone, source = "detected"
                             ◀───────────  user (with time_zone + org_time_zone)
4. session (localStorage) updated
```

- This also happens **every time the app opens** (`useSession` → `fetchMe` → `syncTimeZone`), not only at login.
- If the zone is already the same, no call is made.
- If the call fails, the app keeps working with the old zone.
- An invalid zone name (`"Mars/Base"`) → `400`.

Frontend code: `src/modules/Auth/services/index.ts` → `syncTimeZone()`,
`src/modules/Auth/hooks/index.ts`.

### 3.1 Response of login / me / time-zone

```json
{
  "user_id": "…",
  "org_id": "…",
  "name": "Rahul Verma",
  "email": "student@campus.test",
  "role": "student",
  "time_zone": "America/New_York",
  "org_time_zone": "Asia/Kolkata"
}
```

`time_zone` = where the user is (may be `null` until the browser has reported it),
`org_time_zone` = the college's campus time.

---

## 4. Creating an event / reminder — what to send

### 4.1 On screen

The form always works in **the browser's local time** — DayPreview, the clash check,
the "not before today" validation, all local. The calendar package (`src/calendar`)
knows nothing about time zones; it only sees local time.

Conversion happens only in the module's API layer:
`src/modules/Calendar/services/api.ts`.

### 4.2 Which zone

| Item | Zone (`zoneFor(draft)`) |
|---|---|
| New event (PPT, test, training…) | `session.user.org_time_zone` (campus time) |
| New reminder (`my_reminder`) | The browser's zone |
| Editing an existing item | Its existing `time_zone` (`draft.timeZone`) |

### 4.3 Conversion

A user in London picks **10:00 AM**; the campus is in Sydney:

```
browser local  2026-10-28 10:00 (Europe/London)
   → instant   2026-10-28T10:00:00Z
   → Sydney    2026-10-28 21:00 (Australia/Sydney)
```

### 4.4 Payload (`POST /calendar/events`, `PUT /calendar/events/{id}`)

```json
{
  "event_type": "ppt",
  "title": "TCS Pre-Placement Talk",
  "event_date": "2026-10-28",
  "end_date": "2026-10-28",
  "start_time": "21:00",
  "end_time": "22:30",
  "time_zone": "Australia/Sydney",
  "recurrence": { "freq": "weekly", "interval": 1, "until": "2026-12-31" }
}
```

- `event_date` / `start_time` / `end_time` = the date and time **on the `time_zone` clock**.
- `time_zone` is optional. If it is left out the backend picks it: event → org zone,
  reminder → user zone (`calendar_user.time_zone`, else the org zone).
- An invalid zone name → `422`.
- An all-day item (deadline, reminder without a time) has `start_time: null` — the
  date is sent as it is, with no conversion.
- Recurring: the backend creates every occurrence **in the item's zone**, so
  "every week at 9 PM Sydney" stays 9 PM Sydney across DST changes.

### 4.5 What the backend stores

`apply_payload(event, payload, zone)`:

```
event.event_date = payload.event_date
event.start_at   = to_utc(event_date, start_time, zone)   # UTC instant
event.end_at     = to_utc(end_date,  end_time,  zone)
event.time_zone  = zone
```

Every conversion goes through `app/services/clock.py` — each function takes the zone's name:
`to_utc`, `local_time`, `local_date`, `in_zone`, `zone_label`, `is_zone`, `zone_of`, `canonical_zone`.

---

## 5. Reading events — what the API returns

`GET /calendar/events`, `GET /calendar/coming-up`:

```json
{
  "event_id": "…",
  "event_date": "2026-10-28",
  "start_time": "21:00",
  "end_time": "22:30",
  "starts_at": "2026-10-28T10:00:00Z",
  "ends_at": "2026-10-28T11:30:00Z",
  "time_zone": "Australia/Sydney"
}
```

| Field | What it is |
|---|---|
| `event_date`, `start_time`, `end_time` | The clock in the item's **own zone** (Sydney) |
| `starts_at`, `ends_at` | UTC instant — **use these for the screen** |
| `time_zone` | The item's zone |

For nudge rows, `starts_at` = when the nudge is sent, and `time_zone` = the viewer's zone.

### 5.1 Frontend mapping (`toEvent` → `shownTimes`)

- Timed item: turns `starts_at` / `ends_at` into a **browser-local** date + time
  for the draft. That is why the grid, list and panel all show local time.
- All-day item: `event_date` as it is.
- `draft.timeZone = time_zone` — after an edit, the times are converted back into this zone.

### 5.2 "Campus time" in the panel

When the item's zone differs from the viewer's, the panel shows an extra row:

| Item | Row |
|---|---|
| Event | **Campus time** — `Wed 9:00 PM · Sydney time (GMT+11)` |
| Reminder | **Set for** — the zone the reminder was created in |

When the zones match, the row is hidden. The row lives in the app's own event view
modal (the calendar package draws no panel): `calendar-frontend/src/modules/Calendar/pages/CalendarPage`
→ `eventDetails`, which calls `helpers/tpo.ts` → `timeThere()`.

> Chrome does not know the short name of some zones (Sydney → `GMT+11`, not
> `AEDT`), so the city name is shown alongside.

---

## 6. Notification (bell) text

A notification is worded **when it is read**, in the reader's zone:

```
New event: TCS Pre-Placement Talk on 28 Oct, 06:00 EDT. Check your calendar.
```

- Zone = `calendar_user.time_zone`, else the org zone (`viewer_zone()`).
- The zone's short name (`IST`, `EDT`, `GMT`…) is included, so nobody is confused.
- Code: `calendar_service.notifications_for()`.

---

## 7. Nudges — when they arrive

### 7.1 Which nudge follows which clock

| Nudge | When | Clock |
|---|---|---|
| `event_day_before` | Event start − N days (Settings) | **The event's instant** — the same moment for everyone |
| `event_hour_before` | Event start − N hours | **The event's instant** |
| `assessment_day` | **8:00 AM** on the test day | **The student's zone** |
| `deadline_days_before` | Deadline − N days, **9:00 AM** | **The student's zone** |
| `deadline_last_day` | **9:00 AM** on the deadline day | **The student's zone** |
| `reminder_alert` | Reminder time − (15 min / 1 hour / 1 day); all-day → 9:00 | **The reminder's zone** |

The student's zone = `calendar_user.time_zone`, else the org zone (`nudges.student_zone()`).

### 7.2 Quiet hours and the daily limit

- Quiet hours (default **10 PM – 7 AM**) are counted in **the student's zone**.
  A nudge that falls in quiet hours goes out when they end (7 AM for the student).
- The daily limit (default **3**) is also counted against the student's "today".
- Each college has its own settings (`calendar_settings`, the row with its `org_id`).
- Nudge text uses the student's zone with a zone label: `Your online test is today (06:00–07:00 EDT)…`
- The runner runs every 60 seconds (`run_due`).

### 7.3 When a student's zone changes

When `PUT /auth/me/time-zone` changes the zone, `nudges.move_to_zone()` runs:

- `assessment_day`, `deadline_days_before`, `deadline_last_day` that are still
  **scheduled** → **the same wall-clock time, in the new zone**.
  (8 AM IST becomes 8 AM New York.)
- `event_*` and `reminder_alert` **do not move** — they are tied to the actual
  moment of the event / reminder.
- If a row for that nudge already exists at the new time (moving back to an
  earlier zone), the existing row stays and no duplicate is created.
- If this fails, the user's zone is still saved; the error is logged.

### 7.4 When the college's zone changes

When the Super Admin picks a new zone in Settings, or the first staff sign-in detects
one, `nudges.move_org_to_zone()` moves the pending morning nudges of every student
**who has no zone of their own** — they were on the old campus clock and now follow
the new one. Students with their own zone are not touched.

### 7.5 Deadline nudges are worked out again every minute

The runner recomputes each student's deadline nudges every tick (9:00 in their zone,
N days before from Settings). A pending row whose time no longer matches — the zone
or the setting changed — is replaced (`nudges._reschedule()`), so a student never
gets the same deadline nudge twice at two different times. Event nudges already
scheduled keep their time when Settings change.

---

## 8. Example: an Indian account used from abroad

An account was created in India (zone IST), then someone signs in to it from **New York**.

| Thing | What happens |
|---|---|
| The user's zone | `America/New_York` as soon as they sign in |
| Events in the calendar | Shown in New York time, with "Campus time … (IST)" in the panel |
| "Test today" nudge | 8 AM **New York** time |
| Deadline nudge | 9 AM **New York** time |
| "1 hour before" nudge | 1 hour before the event (the actual moment) |
| A nudge falling at night | After quiet hours, 7 AM New York time |
| An earlier reminder (9 AM IST) | Still fires at 9 AM IST (the actual moment); if that is in quiet hours, at 7 AM |
| Bell text | New York time + `EDT` / `EST` |
| The college zone (a TPO / Admin signed in) | **Does not change** — stays IST |

> **One account = one zone** — the zone of the latest sign-in. If two people in
> different countries use the same account, nudges follow whoever signed in last.
> One account per person is the right setup.

---

## 9. Super Admin — Settings page

`/super-admin/settings` → **Campus time zone** dropdown:

- Every zone the browser knows (`Intl.supportedValuesOf('timeZone')`), with its current short name.
- Save → `PUT /settings` with `"time_zone": "Australia/Sydney"` → source `admin`.
  After that, no sign-in changes it.
- If `time_zone` is not sent, the college's zone **stays as it is**.
- Nudge settings apply **only to that college** (`Settings for your college`).

```json
PUT /settings
{
  "event_reminder_days_before": 1,
  "event_reminder_hours_before": 1,
  "deadline_reminder_days_before": 2,
  "deadline_reminder_same_day": true,
  "daily_nudge_limit": 3,
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "07:00",
  "time_zone": "Australia/Sydney"
}
```

---

## 10. Calendar sync (.ics)

`GET /calendar/feed.ics?token=…` sends every timed event in **UTC** (`DTSTART:20261028T100000Z`),
from `starts_at` / `ends_at`. Google Calendar / Outlook show it in the
user's own zone. All-day items are sent with `VALUE=DATE`.

---

## 11. Database and migrations

| Migration | What it adds |
|---|---|
| `d4b2e6f8a031` | `calendar_settings.org_id` + `time_zone` (unique index `ix_calendar_settings_org`), `calendar_user.time_zone`, `calendar_event.time_zone`, `calendar_reminder.time_zone`; existing data filled with `Asia/Kolkata` |
| `e5c3f7a9b142` | `calendar_settings.time_zone_source` (`default` / `detected` / `admin`) |
| `f6d4a8b0c253` | Old zone names renamed to current ones (`Asia/Calcutta` → `Asia/Kolkata` …) in all 4 tables |

```bash
cd calendar-backend
make db-up      # runs every pending migration, then seeds the template settings row and the users
make run        # starts the API — it does NOT run migrations
```

- **Existing database** (after pulling this change): `make db-up` applies only the
  missing migrations; your data stays. Then `make run`.
- **Fresh database**: `make db-drop` → `make db-up` → `make run`. You get the
  template settings row with `time_zone = DEFAULT_ORG_TIMEZONE` and
  `time_zone_source = "default"`, and the seed users with `time_zone = null`. The
  college's zone is then set by its first staff sign-in.
- `make run` on its own never changes the schema — always `make db-up` after pulling.

`.env` → `DEFAULT_ORG_TIMEZONE=Asia/Kolkata` — used until a college's zone is set.

The `calendar_settings` row without an `org_id` is the **template** — a new
college's row is copied from it (`settings_service.current_row`).

---

## 12. Using this in another repo

The calendar package (`src/calendar`) needs nothing — it only sees local time.
The host app has to:

1. **At login / app start**, send the browser's zone:
   `PUT /auth/me/time-zone { "time_zone": Intl.DateTimeFormat().resolvedOptions().timeZone }`.
2. **API → calendar:** turn a timed item's `starts_at` / `ends_at` into a browser-local
   date + `HH:mm` for the draft; keep `time_zone` in `draft.timeZone`.
3. **Calendar → API:** the draft's local date and time → instant → the item zone's clock;
   send `time_zone` with it. New event = org zone, new reminder = browser zone.
4. Optionally, add a "Campus time" row to the app's own event view modal — the calendar
   package has no panel or slot for it; here it is `CalendarPage` → `eventDetails`
   using `helpers/tpo.ts` → `timeThere()`.

Helpers: `src/lib/timeZone.ts` — `browserZone()`, `canonicalZone(zone)`, `wallClockIn(date, zone)`,
`instantIn(day, time, zone)`, `zoneLabel(date, zone)`, `allZones()`.

---

## 13. Where the code is

| Job | File |
|---|---|
| All conversions, zone name aliases | `calendar-backend/app/services/clock.py` |
| Org zone, detection, settings save | `calendar-backend/app/services/settings_service.py` |
| `PUT /auth/me/time-zone` | `calendar-backend/app/routes/auth.py` |
| Event / reminder save + output, notifications | `calendar-backend/app/services/calendar_service.py` |
| Nudges, quiet hours, `move_to_zone` | `calendar-backend/app/services/nudges.py` |
| .ics feed | `calendar-backend/app/services/ics.py` |
| Browser zone helpers | `calendar-frontend/src/lib/timeZone.ts` |
| Zone sync at sign-in | `calendar-frontend/src/modules/Auth/services/index.ts`, `hooks/index.ts` |
| API ↔ local conversion | `calendar-frontend/src/modules/Calendar/services/api.ts` |
| "Campus time" row | `calendar-frontend/src/modules/Calendar/pages/CalendarPage/index.tsx` (`eventDetails`) + `helpers/tpo.ts` (`timeThere`) |
| Settings picker | `calendar-frontend/src/modules/Settings/pages/SettingsPage/index.tsx` |

---

## 14. How it was tested

| Test | What was checked | Result |
|---|---|---|
| Backend (API) | First TPO sign-in from Sydney → college Sydney; later from London → college stays Sydney; invalid zone rejected; student India → New York moves the test-day nudge to 8:00 AM EST; "1 hour before" does not move; an admin-chosen zone is not changed by sign-ins | 8/8 |
| Browser — 4 zones | TPO in London (campus Sydney) creates an event → saved in the Sydney zone, London time shown, "Campus time" row; student in New York → NY time + EDT notification; student reminder in the NY zone; the same TPO from Sydney → Sydney time, no extra row; Settings picker; no page errors | 22/22 |
| Existing suites | flow 21/21, extra 12/12, student, repeat-rem 15/15, cancelled, dnd 6/6 | Pass |
| Full e2e (TPO + student, events, audience, reminders, real nudges, notifications) | 40/40 | Pass |
| India (browser on IST) | New college: first TPO sign-in from India → college `Asia/Kolkata`; event time saved with no shift (IST − 5:30 = UTC); no "Campus time" row in India; student sees the same time + an "IST" notification; reminder on IST; online test on IST; the same student from New York → NY time + "Kolkata time (GMT+5:30)"; back in India → IST | 22/22 |
| Worldwide — API | 16 campus zones (India, Tokyo, Kathmandu +5:45, Dubai, Singapore, London, Berlin, New York, Los Angeles, São Paulo, Lagos, Nairobi, Johannesburg, Sydney, Auckland, Honolulu), each with a student in another zone: event saved at 10:00 campus time, same instant for the student, notification text and nudge text in the student's clock and label, test-day nudge at 8:00 student time, day-before / hour-before exactly 24 h / 1 h before, quiet hours 23:30 → 07:00 next day in the student's zone, reminder and its alert in the student's zone, morning nudges follow a student who moves, .ics in UTC; weekly events across the US/UK DST change stay 10:00 local; old zone names stored as current ones | 248/248 |
| Worldwide — browser | 16 student zones × 2 campuses (Kolkata, Sydney): correct local time, "Campus time" row shown only when the offset differs; TPOs in Kathmandu, Honolulu, Lagos and Auckland (late at night) create events for a Sydney campus via the UI | 116/116 |
| Fresh database via `make db-drop` / `make db-up` | All migrations applied; template row `Asia/Kolkata` / `default`; users `null`; first TPO sign-in from Chrome in India sets the college to `Asia/Kolkata`; student sign-in does not | Pass |
| Existing user (zone `null`) | With the college on IST and on Sydney: test-day nudge at 8:00, "1 hour before" at 14:00, notification and new reminder — all on the college's zone | 10/10 |
| Browser — IST / London / New York (after the calendar package went headless) | DB keeps UTC; events stored in the campus zone `Asia/Kolkata`; each viewer sees their own zone, plus the "Campus time" row in the app's event view modal when it differs; reminders in the user's zone; notifications in the viewer's zone (e.g. "05:00 EDT") | 12/12 |

### Bugs found by these tests (fixed)

| Bug | Fix |
|---|---|
| Moving a student's nudges to a new zone crashed (`503`) when a nudge row already existed at the new time | The existing row stays, the moving one is dropped; a failure no longer blocks saving the zone |
| Saving Settings without `time_zone` reset the college to IST | Left out = keep the current zone |
| Chrome in India reports `Asia/Calcutta` | Old names are mapped to current ones on both sides (section 0.5) |
| An event starting late at night (e.g. 11:59 PM, 90 minutes) could not be saved — the Publish dialog forced the end date to the start date, and the defaults did not move the end date past midnight | The end date now follows the end time onto the next day |
| A changed college zone (or a changed "days before" setting) left the old deadline nudge in place and added a new one — two nudges, one at the wrong time | Deadline nudges are re-timed each tick (one pending row each); zone-less students move with the college zone |
| A deadline's nudge said "starts in 1 hour" | "closes in 1 hour" / "closes tomorrow at …" |
| An online assessment was saved with the form's default mode "offline" and no venue | No mode is saved for types that have none |
