# Step 1 — Project setup

## Kya banाya

```
calendar-backend/
├── app/
│   ├── main.py              FastAPI app + CORS
│   ├── conf.py              environ.get(...) — saare env yahin
│   ├── db/
│   │   ├── session.py       engine, SessionLocal, Base, get_db
│   │   └── models.py        6 tables
│   ├── auth/
│   │   ├── users.py         do hardcoded user
│   │   ├── tokens.py        JWT banana / padhna
│   │   └── deps.py          current_user, require_role
│   ├── models/
│   │   ├── request_model.py  Pydantic in
│   │   └── response_model.py Pydantic out
│   ├── routes/
│   │   ├── auth.py          /auth/login, /auth/me
│   │   └── health.py        /health
├── scripts/
│   └── init_db.py           tables + settings row
├── docs/
├── requirements.txt
├── .env.example
└── .gitignore
```

Dhancha `campus-calendar-backend-design.md` §15 se liya gaya hai.

## Commands

```bash
cd /home/billion/Documents/Projects/7Seers/calendar/calendar-backend

mkdir -p app/db app/auth app/models app/routes scripts docs
touch app/__init__.py app/db/__init__.py app/auth/__init__.py \
      app/models/__init__.py app/routes/__init__.py

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Dependencies

`requirements.txt` — design doc §13 ki list, wahi versions:

| Library | Version | Kaam |
|---|---|---|
| `fastapi` | 0.115.2 | routes, Depends |
| `uvicorn[standard]` | 0.32.0 | server |
| `sqlalchemy` | 2.0.36 | ORM |
| `psycopg2-binary` | 2.9.10 | postgres driver (sync) |
| `pydantic` | 2.10.3 | validation (v2) |
| `python-dotenv` | 1.0.1 | `.env` load |
| `PyJWT` | 2.8.0 | token |
| `python-dateutil` | 2.9.0 | date arithmetic |
| `tzdata` | 2024.2 | IANA timezones — `zoneinfo` isi ko padhta hai |

> `email-validator` jaan-boojh kar **nahi** liya. Pydantic ka `EmailStr` usi par
> chalta hai; uske bajaye `request_model.py` me ek pattern laga diya — list me
> ek dependency kam.

## .env

`.env.example` se `.env` banao:

```bash
cp .env.example .env
```

| Key | Default | Kya |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://calendar:calendar@localhost:5440/campus_calendar` | step 2 dekho |
| `JWT_SECRET` | `change-me-in-every-environment` | **har environment me badlo** |
| `JWT_EXPIRY_MINUTES` | 720 | 12 ghante |
| `DEFAULT_ORG_TIMEZONE` | `Asia/Kolkata` | design §3 |
| `DEFAULT_ORG_ID` | `1111...` | POC ka ek org |
| `CORS_ORIGINS` | `http://localhost:5180` | frontend ka port |

> `app/services/` aur `app/clients/` design doc §15 me hain, par abhi unme kuch
> hai nahi — khali folder rakhne ke bajaye jab pehli service/client banegi tab
> bana lenge.
