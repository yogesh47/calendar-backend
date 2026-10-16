# Campus Calendar — install and run (local)

Do repo hain, ek hi folder me rakho:

```
calendar/
├── calendar-backend/     FastAPI + Postgres   → port 8001
└── calendar-frontend/    React + Vite         → port 5180
```

Chahiye: **Python 3.10+**, **Node 20+**, **Docker**.

---

## 1. Database

```bash
docker run -d --name campus-calendar-db \
  -e POSTGRES_USER=calendar \
  -e POSTGRES_PASSWORD=calendar \
  -e POSTGRES_DB=campus_calendar \
  -p 5440:5432 \
  postgres:16-alpine
```

Container pehle se bana ho to sirf: `docker start campus-calendar-db`

---

## 2. Backend

```bash
cd calendar-backend

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # default values waise hi theek hain

PYTHONPATH=. python scripts/init_db.py     # tables + settings ki ek row

PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Check: `curl http://127.0.0.1:8001/health` → `{"status":"ok","database":"up"}`

---

## 3. Frontend

Naya terminal (backend chalta rehne do):

```bash
cd calendar-frontend

npm install
cp .env.example .env               # VITE_API_BASE_URL=http://127.0.0.1:8001

npm run dev -- --port 5180 --strictPort
```

Kholo: **http://localhost:5180**

> Port 5180 hi rakhna — backend ke `.env` me CORS isi port ke liye khula hai.

---

## 4. Login

| Role | Email | Password |
|---|---|---|
| TPO | `tpo@campus.test` | `tpo@1234` |
| TPO (doosra) | `tpo2@campus.test` | `tpo2@1234` |
| Student | `student@campus.test` | `student@1234` |
| Super Admin | `admin@campus.test` | `admin@1234` |
