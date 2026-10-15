# Commands reference

In docs me jo flag aur shortcut **sach me chalte hain**, sirf unka matlab.
Jo kahin use nahi hota, wo yahan nahi hai.

## Docker

| Tukda | Matlab |
|---|---|
| `docker run` | nayi container banakar chalao |
| `-d` | **d**etached — background me chalao, terminal wapas de do |
| `--name campus-calendar-db` | container ka naam. Iske bina Docker apne aap koi naam rakh deta hai |
| `-e POSTGRES_USER=calendar` | **e**nvironment variable container ke andar bhejo |
| `-p 5440:5432` | **p**ort — `bahar:andar`. Machine ka 5440 container ke 5432 par jaayega |
| `postgres:16-alpine` | image ka naam aur tag. `alpine` = chhoti image |
| `docker exec` | **chalu** container ke andar ek command chalao |
| `-it` | **i**nteractive + **t**erminal — tab lagao jab andar baith kar type karna ho. Ek baar ka jawab chahiye to mat lagao |
| `docker ps` | chal rahe containers ki list |
| `--filter name=...` | list me sirf wahi jiska naam match kare |
| `docker start` / `stop` | bani hui container ko chalu / band karo (data rehta hai) |
| `docker rm -f` | container **uda do**. `-f` = **f**orce, chalu ho to bhi. Data bhi jaayega |
| `docker logs` | container ka output dekho |
| `--tail 20` | sirf aakhri 20 line |
| `docker info` | Docker daemon khud chal raha hai ya nahi |
| `--format '{{.ServerVersion}}'` | poora JSON ke bajaye sirf ye field |

## psql

Postgres ka command-line client.

| Flag | Matlab |
|---|---|
| `-U calendar` | **U**ser — kis user se judna |
| `-d campus_calendar` | **d**atabase — kaunsa database |
| `-h localhost` | **h**ost — container ke **bahar** se judte waqt |
| `-p 5440` | **p**ort — bahar se judte waqt. Andar se nahi chahiye |
| `-c "select 1"` | **c**ommand — ye chalao aur bahar aa jao |
| `PGPASSWORD=calendar` | flag nahi, env hai — warna psql password poochta hai |

### Backslash commands — psql ke andar

SQL nahi, psql ke apne shortcut. Semicolon nahi lagta.

| Command | Matlab |
|---|---|
| `\dt` | **d**escribe **t**ables — saari tables |
| `\d calendar_event` | **d**escribe — ek table ke columns, types, indexes, constraints |
| `\q` | **q**uit |

### pg_isready

| Tukda | Matlab |
|---|---|
| `pg_isready -U calendar` | Postgres connections le raha hai ya nahi — sirf haan/na, query nahi chalati |

## Python

| Tukda | Matlab |
|---|---|
| `python3 -m venv .venv` | **m**odule `venv` chalao — is folder ka apna Python environment |
| `source .venv/bin/activate` | us environment me ghus jao. Iske bina `pip install` system Python me chala jaayega |
| `pip install -r requirements.txt` | **r**equirements file se saare packages |
| `python -c "..."` | **c**ommand — file banaye bina ye code chalao |
| `PYTHONPATH=.` | "modules isi folder se dhoondho". Iske bina `scripts/` se chalane par `No module named 'app'` aata hai |

## uvicorn

| Tukda | Matlab |
|---|---|
| `uvicorn app.main:app` | `app/main.py` file me jo `app` naam ka object hai, use chalao |
| `--host 127.0.0.1` | kis address par sune |
| `--port 8001` | kis port par |
| `--reload` | file badalte hi khud restart. **Sirf development me** |

## npm / npx / node

| Tukda | Matlab |
|---|---|
| `npm i -D playwright-core` | **i**nstall, `-D` = dev **D**ependency (production build me nahi jaata) |
| `npm init -y` | `package.json` bana do, `-y` = har sawaal ka jawab yes |
| `npx vite` | package install kiye bina seedha chalao |
| `--port 5180` | kis port par dev server |
| `--strictPort` | port busy ho to **chupchaap doosra mat uthao** — error do |
| `node scripts/verify_login.cjs` | wo script chalao |

## curl

| Tukda | Matlab |
|---|---|
| `-s` | **s**ilent — progress bar mat dikhao |
| `-X POST` | HTTP method |
| `-H 'Content-Type: application/json'` | **H**eader bhejo |
| `-d '{"email":"..."}'` | **d**ata — request ki body |
| `-o /dev/null` | response body kahin mat likho |
| `-w "%{http_code}"` | sirf ye cheez chhapo — yahan status code |
| `--max-time 8` | 8 second se zyada mat ruko |

## Linux

| Tukda | Matlab |
|---|---|
| `mkdir -p a/b/c` | folder banao, `-p` = beech ke folder bhi bana do, aur pehle se ho to error mat do |
| `touch file` | khali file bana do (ya uska time update karo) |
| `cp .env.example .env` | copy |
| `ss -ltn` | **l**istening **t**cp sockets, `-n` = naam ki jagah number |
| `pkill -f "vite --port 5180"` | process maaro. `-f` = poori command line me dhoondho, sirf naam me nahi |
| `2>&1` | error ko bhi normal output me mila do |
| `>/dev/null` | output phenk do |

## Snap

| Tukda | Matlab |
|---|---|
| `snap services docker` | snap wali service chalu hai ya nahi |
| `sudo snap start docker` | chalu karo |

> Is machine par Docker snap se chalta hai. Isliye `systemctl is-active docker`
> **`inactive`** bolta hai jabki Docker chal raha hota hai — wo `docker.service`
> dhoondhta hai, aur snap wala `snap.docker.dockerd` hai.

## DBeaver shortcuts

| Shortcut | Matlab |
|---|---|
| `Ctrl + Shift + N` | nayi database connection |
| `Ctrl + ]` | naya SQL editor |
| `Ctrl + Enter` | editor me jo query par cursor hai, wo chalao |
