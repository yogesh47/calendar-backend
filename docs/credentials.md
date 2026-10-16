# Credentials — login karne ke liye sab kuch

Ye sab **sirf local development** ke liye hai. Users DB me nahi hain, code me
likhe hue hain — `app/auth/users.py`.

## Portal login

Login page: **http://localhost:5180/login**

| Role | Email | Password | Login ke baad kahan jaata hai |
|---|---|---|---|
| **TPO** | `tpo@campus.test` | `tpo@1234` | `/tpo/calendar` |
| **TPO (doosra)** | `tpo2@campus.test` | `tpo2@1234` | `/tpo/calendar` |
| **Student** | `student@campus.test` | `student@1234` | `/student/calendar` |
| **Super Admin** | `admin@campus.test` | `admin@1234` | `/super-admin/settings` |

Sabka naam aur id:

| Role | Naam | User id |
|---|---|---|
| TPO | Priya Sharma | `22222222-2222-2222-2222-222222222222` |
| TPO (doosra) | Arjun Mehta | `44444444-4444-4444-4444-444444444444` |
| Student | Rahul Verma | `33333333-3333-3333-3333-333333333333` |
| Super Admin | Meera Iyer | `55555555-5555-5555-5555-555555555555` |

Sab ek hi college ke hain — org id `11111111-1111-1111-1111-111111111111`.

> Doosra TPO isliye hai ki BRD §5 ka "Other TPOs (same college)" wala rasta
> dekha ja sake: Arjun ko Priya ke events read-only dikhte hain, Priya ke
> My Reminders bilkul nahi, aur edit / cancel / delete par 403 milta hai.

> TPO student ka page nahi khol sakta aur student TPO ka nahi — galat role par
> apne hi calendar par wapas bhej diya jaata hai.

> Super Admin (BRD FR-CAL-27) sirf **Calendar & Nudges** settings dekhta hai.
> Event content par uska koi access nahi: `/calendar/*` par 403 milta hai, aur
> TPO / student ko `/settings` par 403 milta hai.

## Terminal se login karke dekhna ho

```bash
curl -s -X POST http://127.0.0.1:8001/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"tpo@campus.test","password":"tpo@1234"}'
```

Jawab me `access_token` milta hai. Usse apna hi data poochhna:

```bash
curl -s http://127.0.0.1:8001/auth/me -H "Authorization: Bearer <token>"
```

## Database

| Cheez | Value |
|---|---|
| Host | `localhost` |
| Port | **5440** (system wala Postgres 5432 par hai, wo chhua nahi) |
| Database | `campus_calendar` |
| User | `calendar` |
| Password | `calendar` |
| Container | `campus-calendar-db` |

```bash
docker exec -it campus-calendar-db psql -U calendar -d campus_calendar
```

## Ports

| Kya | Address |
|---|---|
| Frontend | http://localhost:5180 |
| Backend API | http://127.0.0.1:8001 |
| API ka apna doc | http://127.0.0.1:8001/docs |
| Postgres | localhost:5440 |

## Password badalna ho

`calendar-backend/app/auth/users.py` me `HARDCODED_USERS` ke andar badal do aur
API restart kar do. DB me kuch nahi badalta.
