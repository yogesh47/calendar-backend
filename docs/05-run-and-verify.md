# Step 5 — Chalana aur jaanchna

## Teen cheezein chalni chahiye

> Command me koi flag samajh na aaye to [`06-commands-reference.md`](06-commands-reference.md) dekho.

| # | Kya | Command | Port |
|---|---|---|---|
| 1 | Postgres | `docker start campus-calendar-db` | 5440 |
| 2 | Backend | neeche | 8001 |
| 3 | Frontend | neeche | 5180 |

### Backend

```bash
cd calendar-backend
source .venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Frontend

```bash
cd calendar-frontend
npx vite --port 5180 --strictPort
```

Phir browser me **http://localhost:5180** — login page aayega.

| Kaun | Email | Password |
|---|---|---|
| TPO | `tpo@campus.test` | `tpo@1234` |
| Student | `student@campus.test` | `student@1234` |

## Jaldi se jaanch

```bash
curl -s http://127.0.0.1:8001/health
# {"status":"ok","database":"up"}

curl -s -X POST http://127.0.0.1:8001/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"student@campus.test","password":"student@1234"}'
```

API ka apna doc: **http://127.0.0.1:8001/docs**

## Browser se poori jaanch

Ek bridge likha hua hai jo asli Chrome me poora flow chalata hai:

Script frontend me hai (backend Python ka hai, usme `node_modules` nahi aata):

```bash
cd calendar-frontend
npm i -D playwright-core
node scripts/verify_login.cjs
node scripts/verify_tpo_flow.cjs
```

Chrome system wala hi use hota hai (`channel: 'chrome'`), alag se download nahi
hota.

13 checks, sab pass:

| # | Kya jaancha |
|---|---|
| 1 | bina login `/` → `/login` |
| 2 | login form dikhta hai |
| 3 | guarded route bina login nahi khulta |
| 4 | galat password → *"Email or password is incorrect"* |
| 5 | aur login page par hi rukta hai |
| 6 | TPO login → `/tpo/calendar` |
| 7 | calendar render hota hai |
| 8 | TPO student ka route nahi khol sakta |
| 9 | reload par session bacha rehta hai |
| 10 | sign out → `/login` |
| 11 | student login → `/student/calendar` |
| 12 | student TPO ka route nahi khol sakta |
| 13 | ek bhi JS error nahi |

## Events hatane ke teen raaste

> Ye **sirf development ke liye** hain. BRD kehta hai ki publish ho chuki event
> kabhi permanently delete nahi hoti — usse cancel kiya jaata hai. Ye routes
> testing ka kooda saaf karne ke liye bane hain.

Pehle token le lo:

```bash
TPO=$(curl -s -X POST http://127.0.0.1:8001/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"tpo@campus.test","password":"tpo@1234"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

**Ek event hatana** — id `GET /calendar/events` se milti hai:

```bash
curl -X DELETE http://127.0.0.1:8001/calendar/events/<event_id> \
  -H "Authorization: Bearer $TPO"
```

**Chuni hui kai events hatana:**

```bash
curl -X POST http://127.0.0.1:8001/calendar/events/bulk-delete \
  -H "Authorization: Bearer $TPO" -H 'Content-Type: application/json' \
  -d '{"event_ids":["<id1>","<id2>"]}'
```
Jawab me `deleted` aur `skipped` dono aate hain — jo id milti nahi, wo skip ho
jaati hai, baaki ka kaam nahi rukta.

**Sab kuch hatana** (`confirm=yes` ke bina chalta hi nahi):

```bash
curl -X DELETE "http://127.0.0.1:8001/calendar/events?confirm=yes" \
  -H "Authorization: Bearer $TPO"
```

Teeno raaste delete ke baad live stream par khabar bhejte hain, isliye khule hue
calendar bina refresh ke apne aap khaali ho jaate hain.

## Jab kuch na chale

| Dikhta hai | Wajah | Ilaj |
|---|---|---|
| `Failed to fetch` login par | CORS — port match nahi | `.env` me `CORS_ORIGINS`, phir API restart |
| `No module named 'app'` | `PYTHONPATH` nahi laga | `PYTHONPATH=.` lagao |
| `database: down` | container band | `docker start campus-calendar-db` |
| `Port 5180 is already in use` | purana vite chal raha hai | `pkill -f "vite --port 5180"` |
| `role "billion" does not exist` | system wala Postgres pakad liya | `DATABASE_URL` me port **5440** hai ya nahi dekho |

## Aage kya

| # | Kaam | Design doc me kahan |
|---|---|---|
| 1 | Pydantic request/response — event ke liye | Pydantic models |
| 2 | `calendar_audience_service` — kaun se student, kitne student | Services |
| 3 | `POST /calendar/audience/count` | Routes |
| 4 | `calendar_deadline_service` — jobs API se deadline nikalna | Services |
| 5 | `GET /calendar/events` | Routes |

Saat sawaal abhi bhi khule hain (`calendar-frontend/docs/README.md` ke aakhri
section me) — timezone, student ke fields, eligibility, notification service,
scheduler, push provider, settings table.
