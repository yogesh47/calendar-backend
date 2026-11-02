# Campus Calendar — Backend docs

> Repo pehli baar chala rahe ho? Seedha [`../setup/README.md`](../setup/README.md) —
> container, DB aur backend run karne ka pura kram wahin hai. DB khali karna ho to
> [`../setup/db-drop-up.md`](../setup/db-drop-up.md), schema badalna ho to
> [`../setup/migrations.md`](../setup/migrations.md).

```
docs/
├── README.md            ← ye file
├── api-reference.md     kaunsi API kis cheez ke liye hai
├── schema.md            tables, columns aur unke peeche ki wajah
├── libraries.md         kaun si library, kyun aur kahan
├── credentials.md       logins, DB, ports
├── timezone.md          time zones: kya bhejna hai, kahan save, nudge kis clock par
├── external-events-design.md  external events (student ke apne / linked / auto) ka design — proposal, abhi bana nahi
└── flows/
    ├── create-event-remember-points.md  yaad rakhne wale points: pehle kya, phir kya (waterfall order)
    ├── create-event-simple.md  sabse simple: event fire kiya to role check, data, nudge, notification, timeline
    ├── create-event.md  event banne ka pura flow, line by line
    ├── create-event-waterfall.md  event banne ka waterfall: kadam, files, tables, mota-mota matlab
    ├── create-event-code.md  event banne ka poora code, block-wise; har line: kya karti hai, kya milta hai
    ├── nudges.md        nudge kab, kahan se, kaise jaata hai
    └── tpo-event.md     TPO kya karta hai, kya hota hai
```

## Kya ban chuka hai

| # | Hissa | Haal |
|---|---|---|
| 1 | Postgres + Alembic migrations (`initial setup` → head `c9e1b3d5f7a2` sync range) — pull ke baad `make db-up` | ✅ |
| 2 | Chaar hardcoded user (2 TPO, student, super admin) + JWT login | ✅ |
| 3 | Calendar API — events, reminders, deadlines, notifications, SSE | ✅ |
| 4 | Super Admin settings (FR-CAL-27) | ✅ |
| 5 | Nudge engine (FR-CAL-25 / 26) — [`flows/nudges.md`](flows/nudges.md) | ✅ |
| 6 | Mobile ke liye API (coming-up, unread-count, push devices, date range) | ✅ |

## Product ka sach kahan hai

Ye docs **kaise bana** batate hain. **Kya banana hai** uska sach
`calendar-frontend/docs/` me hai:

| File | Kya |
|---|---|
| `requirements/campus-calendar-brd.md` | BRD — FR-CAL-01 se 27 |
| `campus-calendar-backend-design.md` | backend ka design |
| `campus-calendar-master.md` | poora master doc |
