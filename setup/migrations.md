# Migrations

Schema **Alembic** sambhalta hai.

---

## Ek line me

Model badlo → migration file bano → `make db-up` → database badal gaya.

```
app/db/models/*.py          tumne yahan likha: "table me ab ye column hai"
        ↓                   make db-revision
setup/migrations/versions/  alembic ne yahan likha: "is column ko jodne ka SQL"
        ↓                   make db-up
Postgres                    database me column aa gaya
```

Model **kya hona chahiye** batata hai. Migration **wahan tak kaise pahunche** batati hai.
Dono chahiye — sirf model badalne se database apne aap nahi badalta.

---

## Folder

```
setup/
├── alembic.ini                   alembic ka config
└── migrations/
    ├── env.py                    DATABASE_URL + models yahan se milte hain
    └── versions/                 har migration ek file
        ├── 8e5c071131a6_initial_setup.py
        ├── 188f4317264a_calendar_user_table.py
        └── 9c1a7d4e2b30_uuid_primary_key_defaults.py
```

`env.py` do cheezein deta hai: `app.conf` se **DATABASE_URL**, aur
`app.db.models` import karke **saari tables** (`Base.metadata`). Isi liye naya
model banao to `app/db/models/__init__.py` me bhi import karna zaroori hai —
warna alembic ko wo dikhega hi nahi.

---

## Migrations ek zanjeer hain

Har file apne se pehli wali ka naam rakhti hai:

```
<base> → 8e5c071131a6   initial setup — saari tables
         188f4317264a   calendar_user table
         9c1a7d4e2b30   uuid primary key defaults        ← head
```

- **head** = aakhri migration
- Database khud yaad rakhta hai wo kis revision par hai (`alembic_version` table me)

`upgrade head` matlab: "jahan ho wahan se head tak jo bhi missing hai, sab chala do."
Isi liye purane database par bhi `db-up` safe hai — jo pehle chal chuki hain wo
dobara nahi chalti, data ko haath nahi lagta.

---

## Chalana

```bash
make db-up        # pending migrations chalao
                  # (+ DB na ho to bana do, settings row aur users daal do)
```

Sirf alembic:

```bash
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini upgrade head
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini current     # DB kis revision par hai
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini history     # poori zanjeer
```

---

## Naya column ya table joda

1. **Model badlo** — `app/db/models/`
   (nayi table hai to `app/db/models/__init__.py` me import bhi karo)

2. **Migration banao:**

   ```bash
   make db-revision m="what changed"
   ```

   Alembic model aur database ko mila kar dekhta hai, aur farak ka SQL likh deta hai.

3. **Jo file bani hai use padho** — `setup/migrations/versions/` me sabse nayi.
   Autogenerate perfect nahi hai; `upgrade()` wahi kar raha ho jo tum chahte ho.

4. **Chalao:**

   ```bash
   make db-up
   ```

---

## Autogenerate kya nahi pakadta

`env.py` me `compare_type=True` hai, to **column ka type** badlega to pakad lega.
Par `compare_server_default` **nahi** hai — matlab:

- **server default** add/remove karna
- table ya column ka **naam badalna** (wo drop + create likh dega, data ud jayega)
- **data** ko ek shakl se dusri me badalna

Ye khud likhni padti hain. `9c1a7d4e2b30_uuid_primary_key_defaults.py` isi ka
example hai — haath se likhi gayi, `op.execute(...)` ke saath.

Khud likhni ho to:

```bash
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini revision -m "what changed"
```

(`--autogenerate` ke bina — khaali `upgrade()` / `downgrade()` milte hain.)

---

## Ulta jaana ho

```bash
PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini downgrade -1     # ek kadam peeche
```

Ye migration ka `downgrade()` chalata hai. Isi liye wo bhi theek likhna chahiye —
bina uske wapas aane ka raasta nahi hota.

Sab kuch naya chahiye to seedha [`db-drop-up.md`](db-drop-up.md) —
`make db-drop` phir `make db-up`. (Saara data chala jayega.)

---

## Galat hone par

| Dikkat | Kya hua | Hal |
|---|---|---|
| `Can't locate revision ...` | DB kisi aisi revision par hai jiski file nahi hai | branch galat hai, ya file delete ho gayi — `history` dekho |
| `Multiple head revisions` | do logon ne alag-alag migration banayi, dono base ek hi | `alembic merge heads` |
| `db-revision` khaali file deti hai | model me koi farak hi nahi, ya naya model `__init__.py` me import nahi hai | import check karo |
| Migration chali par column nahi aaya | wo cheez autogenerate pakadta hi nahi (upar dekho) | haath se likho |

---

## Yaad rakhne layak

- **Jo migration push ho chuki hai use mat badlo.** Doosron ke DB me wo chal chuki hai.
  Theek karne ke liye nayi migration banao.
- **Migration file ko git me commit karo** — model ke saath hi. Model aaye aur
  migration na aaye, to baaki sabka `db-up` toot jayega.
- **`make db-up` idempotent hai** — kitni baar bhi chalao, koi nuksan nahi.
