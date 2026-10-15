# Campus Calendar — Backend

Ye folder batata hai ki backend **kis order me** bana, aur har step me **kya
command chali**. Koi step chhoot jaye to seedha us file par jao.

```
docs/
├── README.md                ← ye file
├── 01-project-setup.md      folder, venv, dependencies
├── 02-database.md           DB banana, connection
├── 03-tables.md             6 tables + settings ki ek row
├── 04-auth-login.md         do hardcoded user, JWT, /auth/login
├── 05-frontend-login.md     login page, route guard
└── 06-run-and-verify.md     sab chalana aur jaanchna
```

## Abhi tak kya ban chuka hai

| # | Step | Haal |
|---|---|---|
| 1 | Project setup — folder + venv + deps | ✅ |
| 2 | DB creation + connection | ✅ |
| 3 | 6 tables + settings row | ✅ |
| 4 | Do hardcoded user + login API | ✅ |
| 5 | Frontend login page + guard | ✅ |
| 6 | End-to-end verify (13 checks) | ✅ |

## Design ka sach kahan hai

Ye docs **kaise banaya** batate hain. **Kya banana hai** uska sach
`calendar-frontend/docs/` me hai:

| Sawaal | Kahan |
|---|---|
| DB, API, scheduler ka design | `campus-calendar-backend-design.md` |
| Behaviour kya ho | `requirements/campus-calendar-brd.md` |
| Dikhega kaisa | `requirements/campus-calendar-ui-spec.md` |

## Teen niyam jo har step me lage

1. **Doosri service ke id par FK nahi** — `student_id`, `company_id`, job ids
   hamare DB me nahi hain, isliye unpar foreign key nahi lagti
2. **DB me UTC** — all-day cheezein `DATE` me, `timestamp` me nahi
3. **Code me comment nahi** — naam khud bol dein
