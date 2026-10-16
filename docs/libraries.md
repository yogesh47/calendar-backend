# Backend ki libraries — kaun si, kyun, aur kahan

`requirements.txt` me 10 lines hain. Har ek yahan samjhayi hai: **kya karti hai**,
**kyun chuni gayi**, **code me kahan dikhti hai**, aur **na hoti to kya karna
padta**.

```
fastapi==0.115.2            sqlalchemy==2.0.36        PyJWT==2.8.0
uvicorn[standard]==0.32.0   psycopg2-binary==2.9.10   python-dateutil==2.9.0.post0
pydantic==2.10.3            python-dotenv==1.0.1      tzdata==2024.2
pydantic-settings==2.6.1
```

Version pin isliye hain ki kal `pip install` karne par koi aur version aakar
cheezein na tode.

---

## 1. `fastapi` — poore API ka dhaancha

**Kya karti hai:** URL ko function se jodti hai, request ka body padh kar
validate karti hai, response ko JSON banati hai, aur `/docs` par Swagger khud
bana deti hai.

**Kyun:** teen wajah —

1. **Type hints hi validation hain.** `payload: EventIn` likhte hi FastAPI khud
   body padhta hai, check karta hai, aur galat hone par 422 deta hai. Flask me ye
   sab haath se likhna padta.
2. **Dependency injection** — `Depends(calendar_user)` se har route me login aur
   role ka check ek line me aa jaata hai (`app/auth/deps.py`).
3. **async** — nudge wala background loop aur SSE stream dono isi ke bharose
   chalte hain.

**Kahan:** `app/main.py` (app + CORS + startup/shutdown), `app/routes/*`,
`app/errors.py` (exception handlers), `app/auth/deps.py`.

```python
@router.post("/events", response_model=EventOut, status_code=201)
def create_event(
    payload: EventIn,                                   # body apne aap validate
    user: Annotated[HardcodedUser, Depends(calendar_user)],  # auth + role
    db: Annotated[Session, Depends(get_db)],                 # DB session
) -> EventOut: ...
```

---

## 2. `uvicorn[standard]` — server jo app ko chalata hai

**Kya karti hai:** FastAPI khud HTTP sun nahi sakta; uvicorn ASGI server hai jo
port par baith kar request lata hai.

**Kyun `[standard]`:** ismein `uvloop` (tez event loop), `httptools` (tez HTTP
parsing), aur `watchfiles` (`--reload` ke liye) aa jaate hain. Inke bina SSE aur
reload dono susth ho jaate.

**Kahan:** kisi code me import nahi hota — command me chalta hai:
`uvicorn app.main:app --port 8001 --reload`.

---

## 3. `pydantic` — har andar-bahar jaane wale data ka pehra

**Kya karti hai:** ek class likho, aur wo class request ka JSON padh kar check
karti hai ki har field sahi type ka hai, warna saaf error deti hai.

**Kyun:** ye is project ka sabse zaroori faisla hai —

* **Validation ek hi jagah.** "Offline event me venue chahiye", "end time start
  ke baad hona chahiye", "title 120 se bada nahi" — ye niyam `EventIn` me ek baar
  likhe hain (`app/models/calendar_model.py`), route me nahi. Isliye wahi niyam
  create aur update dono par apne aap lag jaate hain.
* **Galat data DB tak pahunchta hi nahi.** Service layer ko bharosa hai ki jo
  aaya hai wo saaf hai.
* **Error ka message pehle se hi insaani** hai, jise `app/errors.py` ek line me
  badal kar frontend ke toast tak bhejta hai.
* **Out models bhi** (`EventOut`, `NotificationOut`) — response ka shape tay rehta
  hai, galti se koi andaruni field bahar nahi jaata.

**Kahan:** `app/models/calendar_model.py`, `settings_model.py`,
`request_model.py`, `response_model.py`.

```python
class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    ...
    @model_validator(mode="after")
    def check_by_type(self):
        if self.mode == "offline" and not (self.venue or "").strip():
            raise ValueError("Venue is required for an offline event")
        return self
```

**Na hoti to:** har route me `if not body.get("title"): ...` wali 200+ lines, aur
har jagah alag-alag error wording.

---

## 4. `sqlalchemy` — DB se baat, SQL likhe bina

**Kya karti hai:** Python class ↔ Postgres table ka naata; query Python me
likhte hain, SQL wo banati hai.

**Kyun:**

* **Tables code me dikhte hain** (`app/db/models/*`), isliye naya column jodna ek
  line ka kaam hai aur review me dikh jaata hai.
* **SQL injection ka darr nahi** — values hamesha parameter banke jaati hain.
* **Session = transaction.** Event + audience + recipients ek hi `commit()` me
  jaate hain; beech me kuch toota to **poora rollback**, aadha event kabhi nahi
  bachta (`calendar_service.create_event`).
* 2.0 wala naya `select()` style padhne me saaf hai.

**Kahan:** `app/db/session.py` (engine, `SessionLocal`, `Base`, `get_db`),
`app/db/models/*`, aur har service.

```python
rows = db.scalars(
    select(CalendarNudge).where(CalendarNudge.status == "scheduled",
                                CalendarNudge.scheduled_at <= moment)
)
```

**Alembic kyun nahi:** abhi tables `Base.metadata.create_all()` se bante hain
(`setup/init_db.py`). Production me migrations chahiye honge — tab Alembic
jodna hoga.

---

## 5. `psycopg2-binary` — Postgres ka asli driver

**Kya karti hai:** SQLAlchemy khud Postgres se nahi judti; ye driver TCP par
Postgres protocol bolta hai.

**Kyun `-binary`:** compile kiya hua wheel aata hai, isliye `pip install` par
`libpq-dev`/compiler ki zaroorat nahi — kisi bhi machine par seedha chal jaata hai.

**Kahan:** sirf URL me dikhta hai —
`postgresql+psycopg2://calendar:calendar@localhost:5440/campus_calendar`
(`app/conf.py`). Code me kahin import nahi hota.

---

## 6. `python-dotenv` — `.env` padhne ke liye

**Kya karti hai:** `.env` file ko process ke environment me load kar deti hai,
taaki `environ.get("DATABASE_URL")` kaam kare.

**Kyun:** password, JWT secret aur port code me likhna theek nahi; `.env`
gitignored hai aur har machine par alag ho sakta hai (`.env.example` sabko bata
deta hai ki kaun si key chahiye).

**Kahan:** `app/conf.py` ki pehli do lines — `load_dotenv()`.

---

## 7. `PyJWT` — login ka token

**Kya karti hai:** user ki details ko sign karke ek token banati hai
(`issue_token`), aur wapas aane par signature check karke padhti hai
(`read_token`).

**Kyun:**

* **Server par session rakhne ki zaroorat nahi** — token khud bata deta hai ki
  kaun hai, kis org ka hai, kaunsa role hai. Isi se mobile app aur web dono ek hi
  API use kar lete hain.
* `exp` ki wajah se token apne aap expire hota hai (12 ghante), aur expire hote hi
  frontend login par bhej deta hai.
* Library chhoti hai aur sirf yahi ek kaam karti hai.

**Kahan:** `app/auth/tokens.py`; use `app/auth/deps.py` aur SSE stream me hota hai.

```python
payload = {"sub": user.user_id, "org_id": user.org_id, "role": user.role,
           "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)}
return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM), expires_in
```

---

## 8. `tzdata` — timezone ka data

**Kya karti hai:** `zoneinfo.ZoneInfo("Asia/Kolkata")` ko chalne ke liye IANA
timezone database chahiye; Linux par wo system me hota hai, par Windows/slim
Docker images me nahi. Ye package wahi data saath le aata hai.

**Kyun zaroori:** poora calendar isi par tika hai — frontend IST bhejta hai,
`clock.to_utc()` usse UTC me badal kar DB me rakhta hai, aur padhte waqt
`local_time()` wapas IST deta hai. Timezone data na mile to app boot par hi
girti.

**Kahan:** `app/services/clock.py` (`ORG_TIMEZONE`), aur `nudges.py` ka har
"8:00 AM", "quiet hours" wala hisaab.

---

## 9. `pydantic-settings` — abhi use nahi ho rahi

`app/conf.py` seedha `environ.get(...)` use karta hai, isliye ye package filhal
**bekaar pada hai**. Do raaste:

* hata do — ek line kam, ya
* `conf.py` ko `BaseSettings` class me badal do (tab har setting ka type aur
  default ek jagah type-checked ho jaayega).

Abhi tak `requirements.txt` me isliye bachi hai ki setup ke waqt soch thi
settings class banane ki.

---

## 10. `python-dateutil` — abhi use nahi ho rahi

Date ka saara kaam Python ke apne `datetime` + `zoneinfo` se ho jaata hai
(`clock.py`, `nudges.py`). `dateutil` ki zaroorat tab padti jab dhundhli dates
parse karni hoti ("next tuesday") ya `rrule` se repeat events banane hote.

**Repeat events (abhi BRD me nahi hain)** jab aayenge, tab iski `rrule` kaam
aayegi — isliye list me chhodi hai.

---

## Dev ke liye (requirements me nahi)

| Tool | Kaam | Install |
|---|---|---|
| `ruff` | lint + import order (`ruff check app scripts`) | `pip install ruff` |
| `playwright-core` | browser test scripts (frontend repo me) | frontend ka `npm install` |

Ye runtime deps nahi hain, isliye `requirements.txt` se bahar rakhe hain.

---

## Ek nazar me

| Library | Ek line me kyun |
|---|---|
| fastapi | routes + validation + auth injection + Swagger, sab ek jagah |
| uvicorn[standard] | app ko chalane wala tez ASGI server (SSE aur reload ke saath) |
| pydantic | har niyam ek hi jagah, aur error ka message pehle se insaani |
| sqlalchemy | tables code me, query Python me, transaction safe |
| psycopg2-binary | Postgres ka driver, bina compile kiye install |
| python-dotenv | secrets `.env` me, code me nahi |
| PyJWT | stateless login — web aur mobile ek hi API par |
| tzdata | IST ↔ UTC ka hisaab har machine par sahi |
| pydantic-settings | abhi unused — settings class banegi to kaam aayegi |
| python-dateutil | abhi unused — repeat events ke liye rakhi hai |
