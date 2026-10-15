# Step 5 — Frontend login

Frontend: `calendar-frontend` (Vite + React 19 + Tailwind), port **5180**.

## Kya joda

```
src/modules/Auth/
├── types/index.ts                 Role, AuthUser, Session
├── constants/index.ts             API base, storage key, routes, saari copy
├── services/index.ts              login(), fetchMe(), session read/write/clear
├── hooks/index.ts                 useSession()
├── components/RequireAuth/        route guard
└── pages/LoginPage/               login screen
```

## Routing

`src/app/App.tsx`:

| Route | Kaun khol sakta hai |
|---|---|
| `/login` | sab. Pehle se logged in ho to apne calendar par bhej deta hai |
| `/tpo/calendar` | **sirf tpo** |
| `/student/calendar` | **sirf student** |
| `/` aur baaki sab | logged in → apna calendar, warna `/login` |

Galat role ka route kholo to apne wale par bhej deta hai — 403 ka page nahi
dikhता.

## Session kahan rehta hai

`localStorage` me, key `campus-calendar-session`:

```json
{ "token": "eyJ…", "user": { "user_id": "…", "role": "tpo", … } }
```

Har page load par `useSession` token ko **`/auth/me` se jaanchta hai**. Server
mana kar de to session mita diya jaata hai aur banda `/login` par. Isi liye
token expire hone par bhi purana naam screen par nahi tikta.

Jab tak ye jaanch chal rahi hai, guard `Loading…` dikhata hai — warna ek pal ke
liye login page flash hota.

## Login ke baad kahan

`constants/index.ts` me:

```ts
export const HOME_BY_ROLE = {
  tpo: '/tpo/calendar',
  student: '/student/calendar',
}
```

Role hi tay karta hai, login page nahi.

## Frontend ka env

`calendar-frontend/.env`:

```
VITE_API_BASE_URL=http://127.0.0.1:8001
```

## CORS — ek baat yaad rakhne layak

Backend ka `CORS_ORIGINS` frontend ke port se **match karna chahiye**. Pehle
`5173` tha aur frontend `5180` par chal raha tha — browser me `Failed to fetch`
aata tha, jabki `curl` se API bilkul theek chal rahi thi.

```
CORS_ORIGINS=http://localhost:5180,http://127.0.0.1:5180
```

Port badlo to **dono jagah** badalna.
