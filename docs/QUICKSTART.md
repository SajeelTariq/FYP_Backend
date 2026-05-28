# Quick Start — Local Setup

## Prerequisites

- **Python 3.10** — [python.org/downloads](https://www.python.org/downloads/)
- **PostgreSQL 14+** — [postgresql.org/download](https://www.postgresql.org/download/)
- **Docker Desktop** — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) (runs Redis)
- **Git**

---

## Step 1 — Clone the repo

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

Verify Python version:
```bash
python --version   # should print Python 3.10.x
```

---

## Step 3 — Install dependencies

```bash
pip install -r requirements_server.txt
```

> Use `requirements_server.txt`, not `requirements.txt` (the latter is a full frozen dump and may have encoding issues).

---

## Step 4 — Configure environment variables

```bash
cp .env.example .env        # Mac/Linux
copy .env.example .env      # Windows
```

Open `.env` and fill in all values. See the [Environment Variables](#environment-variables) section below.

---

## Step 5 — Create the PostgreSQL database

In psql or pgAdmin:
```sql
CREATE DATABASE competitor_monitoring;
```

Make sure the user/password in `.env` matches your local PostgreSQL setup.

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

To start it again after a system restart:
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

## Environment Variables

Copy `.env.example` as your base. Below is every variable explained.

### Django Core

| Variable | Description | Example |
|---|---|---|
| `DJANGO_SECRET_KEY` | Any long random string — generate at [djecrety.ir](https://djecrety.ir) | `django-insecure-abc123...` |
| `DEBUG` | `True` for local dev | `True` |
| `ALLOWED_HOSTS` | Keep as-is for local | `localhost,127.0.0.1` |

### PostgreSQL

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_DB` | Database name you created | `competitor_monitoring` |
| `POSTGRES_USER` | PostgreSQL username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL password | *(set during PG install)* |
| `POSTGRES_HOST` | Keep as `localhost` for local | `localhost` |
| `POSTGRES_PORT` | Keep as default unless changed | `5432` |

### Redis & Celery

Keep these as-is if you ran Redis on the default port via Docker.

| Variable | Value |
|---|---|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` |
| `REDIS_HOST` | `localhost` |
| `REDIS_PORT` | `6379` |

### External API Keys

| Variable | Where to get it | Used for |
|---|---|---|
| `FIRECRAWL_API_KEY` | [firecrawl.dev](https://firecrawl.dev) | Competitor link extraction |
| `OPENROUTER_API_KEY` | [openrouter.ai](https://openrouter.ai) | AI report generation |
| `APIFY_API_TOKEN` | [apify.com](https://apify.com) | LinkedIn/social media scraping |
| `FMP_API_KEY` | [financialmodelingprep.com](https://financialmodelingprep.com) | Financial data (dashboard) |
| `SENDGRID_API_KEY` | [sendgrid.com](https://sendgrid.com) | Alert email delivery |
| `DEFAULT_FROM_EMAIL` | Verified SendGrid sender | `TrackRival <you@example.com>` |

### CORS (Frontend)

| Variable | Value |
|---|---|
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:5173` |

---

## Setup Checklist

- [ ] Python 3.10 venv activated
- [ ] `pip install -r requirements_server.txt` done
- [ ] `.env` created and filled in
- [ ] PostgreSQL database `competitor_monitoring` created
- [ ] `python manage.py migrate` ran without errors
- [ ] Superuser created
- [ ] Playwright browsers installed (`python -m playwright install chromium`)
- [ ] Redis container running (`docker ps | grep redis`)
- [ ] Celery worker running in a separate terminal
- [ ] Django server running at `http://localhost:8000`

---

## Troubleshooting

**`psycopg2` connection error** — Check `POSTGRES_*` values in `.env` match your local PostgreSQL setup.

**`redis.exceptions.ConnectionError`** — Make sure the Redis container is running: `docker ps | grep redis`

**`ModuleNotFoundError`** — Make sure the venv is activated and `pip install -r requirements_server.txt` was run.

**Playwright browser not found** — Run `python -m playwright install chromium` again.

**Celery tasks stuck in `pending`** — Celery worker must be running. Start it with the command in Step 10.
