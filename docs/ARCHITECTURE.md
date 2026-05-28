# Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         React Frontend                           │
└─────────────────────────────┬────────────────────────────────────┘
                              │ HTTP / REST (Token auth)
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Django REST API                            │
│                                                                  │
│  apps/accounts    — auth, roles, users, RBAC, alert prefs        │
│  apps/monitoring  — competitors, HTML snapshots, diff detection  │
│  apps/scraping    — Celery scraping tasks                        │
│  apps/social_media — LinkedIn posts, jobs, follower snapshots    │
│  apps/dashboard   — 40+ read-only analytics endpoints            │
│  apps/reports     — AI report generation, PDF export             │
│  apps/analytics   — metrics & trend analysis models              │
│  apps/rag         — Chroma vector DB                             │
└────────────────┬─────────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐   ┌──────────────┐
│  PostgreSQL  │   │    Redis     │
│  (main DB)   │   │ (task queue) │
└──────────────┘   └──────┬───────┘
                          │
                          ▼
               ┌──────────────────────┐
               │    Celery Workers    │
               │  + Celery Beat       │
               │    (cron scheduler)  │
               └──────────┬───────────┘
                          │
          ┌───────────────┼───────────────────┐
          ▼               ▼                   ▼
  ┌──────────────┐ ┌────────────┐  ┌──────────────────┐
  │  Firecrawl   │ │   Apify    │  │  OpenRouter API  │
  │  (link map)  │ │ (LinkedIn) │  │   (LLM / AI)     │
  └──────────────┘ └────────────┘  └──────────────────┘
          ▼
  ┌──────────────┐   ┌────────────┐   ┌──────────────┐
  │  Playwright  │   │  FMP API   │   │  SendGrid    │
  │ (HTML scrape)│   │(financials)│   │   (email)    │
  └──────────────┘   └────────────┘   └──────────────┘
```

---

## Django Apps

| App | Responsibility |
|---|---|
| `accounts` | Registration, login, logout, token auth. Role and user management (RBAC). Per-page permissions. Alert email preferences. |
| `monitoring` | Competitor CRUD. HTML snapshots (daily scrapes). Diff detection between snapshots — stores added/removed/modified lines with an LLM-generated summary. |
| `scraping` | Celery tasks for the website pipeline: link extraction (Firecrawl), HTML scraping (Playwright), metadata extraction (BeautifulSoup). Daily cron trigger. |
| `social_media` | LinkedIn data via Apify: company posts, job postings, follower/employee snapshots. |
| `dashboard` | Read-only analytics endpoints consumed by the frontend dashboard. Covers financial data (FMP), website changes, social media, hiring, trends. |
| `reports` | AI-generated PDF reports (executive and analyst types) over a user-defined date range. Uses OpenRouter to generate content from aggregated competitor data. |
| `analytics` | `CompetitorMetrics` and `TrendAnalysis` models — populated by background tasks. |
| `rag` | Chroma vector DB integration for semantic search over scraped content. |

---

## Cron Schedule (Celery Beat)

| Time | Task | What it does |
|---|---|---|
| 2:00 AM daily | `run_daily_monitoring` | Scrapes all competitor websites, diffs against last snapshot, generates LLM summaries, creates `website_change` and `new_page` alerts, sends email notifications |
| 3:00 AM daily | `run_linkedin_monitoring` | Runs Apify actors for all competitors with a `linkedin_url`: scrapes company posts, job listings, follower/employee counts. Creates `new_job` and `follower_change` alerts, sends email notifications |
| Every 2 hours | `fetch_competitor_news` | Fetches recent news articles for each competitor using their `website_base_url` as a search signal. Deduplicates against existing articles. |

---

## Website Monitoring Pipeline

```
Celery Beat → run_daily_monitoring()
    │
    ├── For each competitor:
    │       │
    │       ├── 1. Firecrawl API  → discover all subpage URLs
    │       │
    │       ├── 2. Playwright     → scrape HTML for each URL
    │       │                       store as HTMLSnapshot
    │       │
    │       ├── 3. Diff engine    → compare new snapshot vs previous
    │       │                       classify: added / removed / modified
    │       │                       flag significant changes (threshold-based)
    │       │
    │       ├── 4. LLM summary    → OpenRouter generates a 1-line summary
    │       │                       for each significant change
    │       │
    │       └── 5. Alerts         → create Alert records in DB
    │                               send email via SendGrid if preference set
    │
    └── Done
```

---

## LinkedIn Monitoring Pipeline

```
Celery Beat → run_linkedin_monitoring()
    │
    ├── For each competitor with linkedin_url:
    │       │
    │       ├── Apify Actor 1 (company profile)
    │       │       → posts (last ~30 days) → SocialMediaPost
    │       │       → follower count        → SocialMediaSnapshot
    │       │       → employee count        → SocialMediaSnapshot
    │       │
    │       └── Apify Actor 2 (job listings)
    │               → new / updated / deactivated jobs → JobPosting
    │               → creates new_job alerts for new postings
    │
    └── Follower spike check → creates follower_change alert if ≥5% change
```

---

## Authentication

All API endpoints (except register and login) require a token in the `Authorization` header:

```
Authorization: Token <your_token>
```

Tokens are issued on login and persist until logout. Each user's data (competitors, reports, alerts) is fully isolated — queries are automatically filtered to `request.user`.

---

## RBAC (Role-Based Access Control)

- A `super_admin` user can create roles and assign them to users.
- Each role has a `RolePermission` record with boolean flags for each frontend page: `dashboard`, `competitors`, `ai_assistant`, `reports`, `settings`, `alerts`.
- The frontend reads `GET /api/accounts/me/permissions/` on load to show/hide pages.
- `super_admin` always has full access regardless of role permissions.

---

## External Services Summary

| Service | Used for | Required |
|---|---|---|
| Firecrawl | Mapping all subpage URLs of a competitor website | Yes (scraping) |
| Playwright | Rendering and capturing HTML of competitor pages | Yes (scraping) |
| Apify | LinkedIn company scraping (posts, jobs, snapshots) | Yes (LinkedIn monitoring) |
| OpenRouter | LLM calls for change summaries and report generation | Yes (AI features) |
| FMP (Financial Modeling Prep) | Market cap, income statements, ratios, executive data | Optional (financial dashboard) |
| SendGrid | Transactional alert emails | Optional (email alerts) |
| Chroma (local) | Vector DB for RAG semantic search | Optional (RAG) |
