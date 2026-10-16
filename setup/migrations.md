# Migrations

Schema **Alembic** sambhalta hai. Sab kuch isi folder me hai:

```
setup/
├── alembic.ini                  alembic ka config
└── migrations/
    ├── env.py                   DATABASE_URL + models yahan se milte hain
    └── versions/
        └── 8e5c071131a6_initial_setup.py    saari 7 tables
```

Abhi ek hi migration hai — **`initial setup`** — jo poora schema banati hai:
`calendar_event`, `calendar_event_audience`, `calendar_event_recipient`,
`calendar_reminder`, `calendar_nudge`, `calendar_push_device`,
`calendar_settings` — indexes aur unique constraints ke saath.

---

## Chalana

```bash
make db-up        # pending migrations chalao (+ DB na ho to bana do, settings row daalo)
```

Sirf alembic chalana ho:

```bash
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini upgrade head
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini current     # DB kis revision par hai
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini history     # saari migrations
```

---

## Naya column ya table joda

1. Model badlo — `app/db/models/`
2. Migration banao:

```bash
make db-revision m="what changed"
```

3. Jo file bani hai use ek baar padh lo (`setup/migrations/versions/`), phir:

```bash
make db-up
```

Purane database par bhi `db-up` safe hai — jo missing hai sirf wahi jodta hai,
data ko haath nahi lagata.

---

## Ulta jaana ho

```bash
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini downgrade -1
```

Sab kuch naya chahiye to seedha [`db-drop-up.md`](db-drop-up.md) —
`make db-drop` phir `make db-up`.
