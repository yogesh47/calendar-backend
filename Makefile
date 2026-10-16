PY = .venv/bin/python
DB_CONTAINER = campus-calendar-db

.PHONY: db-init db-start db-stop db-check db-drop db-up db-revision stop run

# Pehli baar: Postgres container banata hai (port 5440).
db-init:
	@docker run -d --name $(DB_CONTAINER) \
		-e POSTGRES_USER=calendar -e POSTGRES_PASSWORD=calendar -e POSTGRES_DB=campus_calendar \
		-p 5440:5432 postgres:16-alpine

# Container chalu / band.
db-start:
	@docker start $(DB_CONTAINER)

db-stop:
	@docker stop $(DB_CONTAINER)

# DB judta hai ya nahi, aur kitni tables hain.
db-check:
	@PYTHONPATH=. $(PY) setup/check_db.py

# Database delete kar deta hai.
db-drop:
	@PYTHONPATH=. $(PY) setup/drop_db.py --yes

# Model badla ho to nayi migration banao.
db-revision:
	@PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini revision --autogenerate -m "$(m)"

# Database + saari tables + settings ki ek row — data khali.
db-up:
	@PYTHONPATH=. $(PY) setup/init_db.py

API_PORT = 8001

# Port 8001 par jo bhi chal raha ho use band karo.
stop:
	@fuser -s -k $(API_PORT)/tcp 2>/dev/null && echo "purana server band kiya" || echo "koi server chal nahi raha tha"

# Purana band karke naya chalu karo (http://127.0.0.1:8001).
run: stop
	@sleep 1
	@PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $(API_PORT) --reload
