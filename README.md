# TrackRival — Backend

Django REST API backend for **TrackRival**, a competitor intelligence platform that automatically monitors competitor websites, LinkedIn activity, job postings, financial data, and news — and surfaces insights through a dashboard, alerts, and AI-generated reports.

## Features

- **Website monitoring** — daily scraping, HTML diff detection, significant-change detection with LLM summaries
- **LinkedIn monitoring** — posts, job postings, follower/employee snapshots via Apify
- **Financial data** — market cap, revenue, growth ratios, executive data via Financial Modeling Prep (FMP) API
- **News feed** — competitor news aggregated every 2 hours
- **AI reports** — executive and analyst PDF reports generated via LLM on any date range
- **Alerts** — email + in-app notifications for website changes, new pages, new jobs, follower spikes
- **Dashboard** — 40+ analytics endpoints covering website changes, social media, hiring signals, trends
- **RBAC** — role-based access control with per-page permissions

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4.2 + Django REST Framework 3.14 |
| Database | PostgreSQL 14+ |
| Task queue | Celery 5 + Redis |
| Web scraping | Playwright (HTML), Firecrawl API (links), Apify (LinkedIn) |
| AI / LLM | OpenRouter API |
| Financial data | Financial Modeling Prep (FMP) API |
| Email | SendGrid |
| Auth | Token-based (DRF) |

## Project Structure

```
backend/
├── apps/
│   ├── accounts/       # Auth, roles, users, RBAC, alert preferences
│   ├── monitoring/     # Competitors, HTML snapshots, diff detection
│   ├── scraping/       # Celery tasks — scraping pipeline, daily cron
│   ├── social_media/   # LinkedIn posts, job postings, follower snapshots
│   ├── dashboard/      # 40+ read-only analytics endpoints
│   ├── reports/        # AI report generation and PDF export
│   ├── analytics/      # Competitor metrics and trend analysis models
│   └── rag/            # RAG system (Chroma vector DB)
├── config/             # Django settings, URL routing, Celery config
├── utils/              # Shared helpers
├── docs/               # Documentation
│   ├── QUICKSTART.md   # Setup guide
│   ├── API_REFERENCE.md # All API endpoints with cURL examples
│   └── ARCHITECTURE.md # System architecture and data flow
├── manage.py
├── requirements_server.txt
└── .env.example
```

## Quick Start

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for full setup instructions.

```bash
# 1. Clone and set up environment
git clone <repo-url> && cd backend
py -3.10 -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements_server.txt

# 2. Configure .env (copy from .env.example and fill in values)

# 3. Run migrations and create superuser
python manage.py migrate
python manage.py createsuperuser

# 4. Start services
docker run -d -p 6379:6379 --name redis redis
celery -A config worker --loglevel=info --pool=solo   # separate terminal
python manage.py runserver
```

API is live at `http://localhost:8000`. Admin panel at `http://localhost:8000/admin`.

## Documentation

| Document | Description |
|---|---|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Step-by-step local setup |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | All endpoints with cURL examples |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |

## Cron Schedule

| Time | Job |
|---|---|
| 2:00 AM daily | Website scraping + HTML diff detection + email alerts |
| 3:00 AM daily | LinkedIn scraping (posts, jobs, snapshots) + email alerts |
| Every 2 hours | News feed refresh |
