# Step 4 — Do hardcoded user aur login

## User DB me kyun nahi hain

Design (§1a) kehta hai: **users hamare nahi hain** — identity SkillsBridge ke
paas hai. Isliye koi `user` table nahi banayi. POC chalane ke liye do user
**code me** rakhe hain, `app/auth/users.py` me. Jis din asli identity service
judegi, sirf ye ek file badlegi.

## Do user

| Role | Email | Password | user_id |
|---|---|---|---|
| **TPO** | `tpo@campus.test` | `tpo@1234` | `2222…2222` |
| **Student** | `student@campus.test` | `student@1234` | `3333…3333` |

Dono ka `org_id` ek hi — `DEFAULT_ORG_ID` (`1111…1111`).

> Password plain text me hain aur password comparison `secrets.compare_digest`
> se hota hai (timing attack se bachne ke liye). **Ye sirf POC ke liye hai** —
> asli identity service aate hi ye file hat jaayegi.

## Token

`app/auth/tokens.py` — PyJWT, HS256.

Payload me kya jaata hai:

```json
{
  "sub": "2222…2222",
  "org_id": "1111…1111",
  "role": "tpo",
  "email": "tpo@campus.test",
  "name": "Priya Sharma",
  "exp": 1792085697
}
```

`org_id` aur `role` token me isliye hain ki har request par inhe dobara dhoondhna
na pade — design §1b ka role check inhi par chalta hai.

## Endpoints

| Method | Path | Kya karta hai |
|---|---|---|
| `POST` | `/auth/login` | email + password → token + user |
| `GET` | `/auth/me` | token → user (frontend reload par isi se jaanchta hai) |
| `GET` | `/health` | app + DB zinda hai ya nahi |

### POST /auth/login

```bash
curl -s -X POST http://127.0.0.1:8001/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"tpo@campus.test","password":"tpo@1234"}'
```

```json
{
  "access_token": "eyJhbGciOi…",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": {
    "user_id": "22222222-2222-2222-2222-222222222222",
    "org_id": "11111111-1111-1111-1111-111111111111",
    "name": "Priya Sharma",
    "email": "tpo@campus.test",
    "role": "tpo"
  }
}
```

Galat password:

```json
{"detail":"Email or password is incorrect"}   // 401
```

Email galat ho ya password — **message ek hi rehta hai**, taaki ye pata na chale
ki kaun si email registered hai.

### GET /auth/me

```bash
curl -s http://127.0.0.1:8001/auth/me -H "Authorization: Bearer $TOKEN"
```

Bina token: `{"detail":"Sign in to continue"}` — 401
Purana/kharab token: `{"detail":"Your session has expired"}` — 401

## Route par role ka pehra

`app/auth/deps.py` do cheezein deta hai:

```python
def tpo_only(user = Depends(require_role("tpo"))):
    ...

def koi_bhi_logged_in(user = Depends(current_user)):
    ...
```

Aage jab calendar ke routes banenge, TPO-only cheezein `require_role("tpo")` ke
peeche jaayengi — design §1b ka capability matrix wahin lagega.
