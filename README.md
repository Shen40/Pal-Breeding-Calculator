# Pal Breeding Calculator

A breeding calculator for Palworld. Track your Pal box, discover what you can breed from the Pals you own (including multi-generation combinations), and calculate the odds of breeding a target Pal with specific passive skills.

## Features

- **Pal inventory** — add Pals to your box with species, gender, and up to 4 passive skills, either as a guest (stored locally in the browser) or as a registered user (stored server-side).
- **Breedable Pals discovery** — see every child species reachable from your current box, including Pals reachable only through multi-step breeding chains (breadth-first search over several generations, not just direct one-step pairs).
- **Target breeding pairs** — pick a target species and desired passives, and get every valid parent pair from your box ranked by success probability, expected number of eggs, and 95th-percentile egg count.
- **Full Pal & passive data** — all 299 Pals with accurate breeding power values and Paldeck indices, 161 special/unique breeding combinations, and all 96 passive skills, each searchable via dropdown.
- **Accounts** — register/log in to persist your box across sessions; guest mode works entirely offline via `localStorage` with no account required.

## Tech stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL (SQLite for local dev), JWT auth (PyJWT + passlib/bcrypt)
- **Frontend**: vanilla JavaScript + Tailwind CSS, served as static files by FastAPI (no separate frontend server)
- **Deployment**: Docker / `docker-compose`, served via Gunicorn managing Uvicorn workers

## Project layout

```
src/
  api/            FastAPI routers and dependencies (auth, pals, breeding)
  core/           config, database session, security, error handling
  engine/         breeding calculation, passive-inheritance probability, reverse lookup
  models/         SQLAlchemy models (User, UserPal)
  schemas/        Pydantic request/response schemas
  services/       BreedingService — the core business logic
data/             pals.json, unique_combos.json, passives.json (loaded at startup)
static/           frontend (index.html, app.js, Tailwind input/output CSS)
alembic/          database migrations
tests/            pytest suite
```

## Local setup

**Prerequisites**: Python 3.11+, Node.js (only for rebuilding Tailwind CSS)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

cp .env.example .env            # then fill in SECRET_KEY / DATABASE_URL
```

By default `DATABASE_URL` can point at a local SQLite file (`sqlite:///./app.db`) for quick local dev, or a real Postgres instance. Generate a real `SECRET_KEY` rather than using a placeholder:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run the app:

```bash
uvicorn src.main:app --reload
```

Open `http://127.0.0.1:8000`.

If you change `static/index.html` or `app.js` and need new Tailwind utility classes to take effect, rebuild the CSS (it's a pre-built static file, not compiled live):

```bash
npx @tailwindcss/cli -i static/input.css -o static/style.css --minify
```

## Database migrations

Schema changes are managed with Alembic:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

In Docker, `alembic upgrade head` runs automatically before the server starts (see `Dockerfile`).

## Running with Docker

```bash
docker compose up -d --build
```

This starts the app plus a local Postgres container. Set `SECRET_KEY` (required) and optionally `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `CORS_ORIGINS` in `.env` — `docker-compose.yml` reads them from there rather than hardcoding secrets.

## Tests

```bash
pytest
```

## API overview

All endpoints are under `/api/v1`:

- `POST /auth/register`, `POST /auth/token`, `GET /auth/me` — account management
- `GET /pals/`, `POST /pals/`, `DELETE /pals/{id}` — manage your Pal box (auth required)
- `GET /breeding/species`, `GET /breeding/passives` — lookup data for dropdowns
- `POST /breeding/discover` — breedable Pals from your box (or a guest `inventory_override`)
- `POST /breeding/find-pairs` — breeding pairs and odds for a target species/passives

Guest mode endpoints accept an `inventory_override` in the request body instead of reading from the database, so the frontend can work fully offline.
