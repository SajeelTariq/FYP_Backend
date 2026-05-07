# Local Development Setup

## Prerequisites

Install these before starting:

- **Python 3.10** — [python.org/downloads](https://www.python.org/downloads/)
- **PostgreSQL 14+** — [postgresql.org/download](https://www.postgresql.org/download/)
- **Docker Desktop** — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) (used to run Redis)
- **Git**

---

## Step 1 — Clone and enter the repo

```bash
git clone <repo-url>
cd backend
```

---

## Step 2 — Create a Python 3.10 virtual environment

**Windows (PowerShell):**
```powershell
py -3.10 -m venv venv
venv\Scripts\Activate.ps1
```

**Mac/Linux:**
```bash
python3.10 -m venv venv
source venv/bin/activate
```

Verify you're on the right Python version:
```bash
python --version   # should print Python 3.10.x
```

---

## Step 3 — Install dependencies

```bash
pip install -r requirements_server.txt
```

> Use `requirements_server.txt`, not `requirements.txt` (the latter is a frozen full-env dump and may have encoding issues).

---

## Step 4 — Set up environment variables

Copy the example file:
```bash
cp .env.example .env        # Mac/Linux
copy .env.example .env      # Windows
```

Then open `.env` and fill in the values. See the [Environment Variables Guide](#environment-variables-guide) below.

---

## Step 5 — Create the PostgreSQL database

Open **psql** (or pgAdmin) and run:
```sql
CREATE DATABASE competitor_monitoring;
```

Make sure the user/password you set in `.env` has access to this database.

---

## Step 6 — Run migrations

```bash
python manage.py migrate
```

---

## Step 7 — Create a superuser

```bash
python manage.py createsuperuser
```

---

## Step 8 — Install Playwright browsers

```bash
python -m playwright install chromium
```

---

## Step 9 — Start Redis (Docker)

Make sure Docker Desktop is running, then:
```bash
docker run -d -p 6379:6379 --name redis redis
```

To start it again after a restart:
```bash
docker start redis
```

---

## Step 10 — Start the Celery worker (new terminal)

Activate the venv in a second terminal, then:
```bash
celery -A config worker --loglevel=info --pool=solo
```

---

## Step 11 — Start the Django server

```bash
python manage.py runserver
```

The API is now live at `http://localhost:8000`.  
Admin panel: `http://localhost:8000/admin`

---

## Environment Variables Guide

Below is every variable in `.env` explained. Copy `.env.example` as the base.

### Django Core

| Variable | What to put | Example |
|---|---|---|
| `DJANGO_SECRET_KEY` | Any long random string — generate one at [djecrety.ir](https://djecrety.ir) | `django-insecure-abc123...` |
| `DEBUG` | `True` for local dev | `True` |
| `ALLOWED_HOSTS` | Keep as-is for local | `localhost,127.0.0.1` |

### PostgreSQL (Local Database)

These should match whatever you set up in your local PostgreSQL installation.

| Variable | What to put | Default / Example |
|---|---|---|
| `POSTGRES_DB` | Name of the database you created | `competitor_monitoring` |
| `POSTGRES_USER` | Your PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | Your PostgreSQL password | whatever you set during PG install |
| `POSTGRES_HOST` | Keep as `localhost` for local | `localhost` |
| `POSTGRES_PORT` | Keep as `5432` unless you changed it | `5432` |

### Redis & Celery

Keep these as-is if you ran Redis on the default port via Docker.

| Variable | Value |
|---|---|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` |
| `REDIS_HOST` | `localhost` |
| `REDIS_PORT` | `6379` |

### External API Keys

These are required for the scraping and AI features. Ask a team member for the keys, or create your own accounts.

| Variable | Where to get it |
|---|---|
| `FIRECRAWL_API_KEY` | [firecrawl.dev](https://firecrawl.dev) — used for competitor link extraction |
| `OPENROUTER_API_KEY` | [openrouter.ai](https://openrouter.ai) — used by the Agno AI agents |
| `APIFY_API_TOKEN` | [apify.com](https://apify.com) — used for LinkedIn/social media scraping |

> The `APIFY_COMPANY_ACTOR_ID` and `APIFY_JOBS_ACTOR_ID` values are already set in `settings.py` as defaults — you don't need to add them to `.env` unless you want to override them.

### CORS (Frontend)

| Variable | Value |
|---|---|
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173` |

---

## Quick Checklist

- [ ] Python 3.10 venv activated
- [ ] `pip install -r requirements_server.txt` done
- [ ] `.env` file created and filled in
- [ ] PostgreSQL database `competitor_monitoring` created
- [ ] `python manage.py migrate` ran successfully
- [ ] Superuser created
- [ ] Playwright browsers installed
- [ ] Redis container running
- [ ] Celery worker running (separate terminal)
- [ ] Django server running

---

## Troubleshooting

**`psycopg2` error on connect** — Check `POSTGRES_*` values in `.env` match your local PostgreSQL setup.

**`redis.exceptions.ConnectionError`** — Make sure the Redis Docker container is running: `docker ps | grep redis`

**`ModuleNotFoundError`** — Make sure the venv is activated and you ran `pip install -r requirements_server.txt`.

**Playwright browser not found** — Run `python -m playwright install chromium` again.
