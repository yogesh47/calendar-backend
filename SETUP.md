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
cd calendar-backend

make db-init      # sirf pehli baar — Postgres container (port 5440)
make db-start     # uske baad har baar
```

Kaam khatam hone par: `make db-stop`

---

## 2. Backend

```bash
cd calendar-backend

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

make db-check                      # DB hai ya nahi
make db-up                         # na ho to bana lo
make run                           # API chalu
```

Check: `curl http://127.0.0.1:8001/health` → `{"status":"ok","database":"up"}`

Detail: [`setup/README.md`](setup/README.md)

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

## 4. Data saaf karna ho (kabhi bhi)

```bash
make db-drop     # database delete
make db-up       # database + saari tables + settings row, data khali
```

Detail: [`setup/db-drop-up.md`](setup/db-drop-up.md)

---

## 5. Login

| Role | Email | Password |
|---|---|---|
| TPO | `tpo@campus.test` | `tpo@1234` |
| TPO (doosra) | `tpo2@campus.test` | `tpo2@1234` |
| Student | `student@campus.test` | `student@1234` |
| Super Admin | `admin@campus.test` | `admin@1234` |
