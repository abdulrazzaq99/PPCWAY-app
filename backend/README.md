# PPCWay backend

Python 3.12, FastAPI, SQLAlchemy, Playwright. One package, `ppcway`, with these parts:

- `crawler/`   the robots-aware, SSRF-safe site reader, ported from the proof of concept with its tests
- `audit/`     the free website audit: crawl, headless render on phone and laptop with screenshots,
               PageSpeed (four Lighthouse categories), site health, local presence, the conversion
               path, and the findings: eight checks plus three under the hood
- `api/`       the HTTP API (`/v1/audits` today)
- `db/`        the SQLAlchemy base and session; `migrations/` is Alembic with its own version table

## Run it locally (Docker, SQLite)

```
cd backend
cp .env.example .env
docker compose up --build
```

That builds the image on Microsoft's Playwright base (Chromium included), migrates a
SQLite file at `backend/data/ppcway.db`, and serves the API on http://localhost:8300.
`src/` is mounted, so a code change needs `docker compose restart api`, not a rebuild.
The Google credentials and `PAGESPEED_API_KEY` are read from `../web/.env`; the
`VERCEL_` database and Redis URLs in that file are for the deployment and are not
read locally. The web app reaches the API through `BACKEND_URL` in `web/.env.local`.

Without Docker:

```
uv venv --python 3.12 && uv pip install -e ".[dev]"
.venv/bin/python -m playwright install chromium
.venv/bin/alembic upgrade head
.venv/bin/uvicorn ppcway.api.app:app --port 8300 --reload
```

Deployed, set `DATABASE_URL` to Neon and `REDIS_URL` to Upstash; the same migrations
run there with Postgres types.

Run one audit from a terminal:

```
.venv/bin/python -m ppcway.cli audit alphaplumbing.ca
```

## Tests

```
.venv/bin/python -m pytest -q
```

The crawler tests ban the network mechanically; the audit tests are pure. Nothing here
runs against the database, which holds real sign-in data from the proof of concept.
