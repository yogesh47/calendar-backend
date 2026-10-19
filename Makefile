PY = .venv/bin/python
DB_CONTAINER = campus-calendar-db

.PHONY: db-init db-start db-stop db-check db-drop db-up db-revision stop run run-local

# First time only: create the Postgres container (port 5440).
db-init:
	@docker run -d --name $(DB_CONTAINER) \
		-e POSTGRES_USER=calendar -e POSTGRES_PASSWORD=calendar -e POSTGRES_DB=campus_calendar \
		-p 5440:5432 postgres:16-alpine

# Start / stop the container.
db-start:
	@docker start $(DB_CONTAINER)

db-stop:
	@docker stop $(DB_CONTAINER)

# Does the database answer, and how many tables does it have.
db-check:
	@PYTHONPATH=. $(PY) setup/check_db.py

# Delete the database.
db-drop:
	@PYTHONPATH=. $(PY) setup/drop_db.py --yes

# Create a new migration after a model change.
db-revision:
	@PYTHONPATH=. .venv/bin/alembic -c setup/alembic.ini revision --autogenerate -m "$(m)"

# Database + every table + one settings row — no data.
db-up:
	@PYTHONPATH=. $(PY) setup/init_db.py

API_PORT = 8001

# Stop whatever is holding port 8001.
stop:
	@fuser -s -k $(API_PORT)/tcp 2>/dev/null && echo "stopped the old server" || echo "nothing was running"

# Stop the old server, then start a fresh one (http://127.0.0.1:8001).
run: stop
	@sleep 1
	@PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $(API_PORT) --reload

# This machine's address on the network, read fresh every time because DHCP changes it.
LAN_IP = $(shell hostname -I | awk '{print $$1}')

# Same server, but open to every device on the same network. The LAN origin is
# added to CORS here, so .env keeps its localhost-only list.
run-local: stop
	@sleep 1
	@echo "API      http://$(LAN_IP):$(API_PORT)"
	@echo "Frontend run: npm run dev:local"
	@PYTHONPATH=. \
		CORS_ORIGINS="http://localhost:5180,http://127.0.0.1:5180,http://$(LAN_IP):5180" \
		.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $(API_PORT) --reload
