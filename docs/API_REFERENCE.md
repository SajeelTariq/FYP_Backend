# API Reference

Base URL: `http://localhost:8000`

All endpoints except **Register** and **Login** require a token header:
```
Authorization: Token <your_token>
```

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Competitors](#2-competitors)
3. [Accounts — Roles & Users](#3-accounts--roles--users)
4. [Alerts](#4-alerts)
5. [Dashboard — Overview](#5-dashboard--overview)
6. [Dashboard — Financial Profile](#6-dashboard--financial-profile)
7. [Dashboard — Financial Health](#7-dashboard--financial-health)
8. [Dashboard — Website Changes](#8-dashboard--website-changes)
9. [Dashboard — Social Media Posts](#9-dashboard--social-media-posts)
10. [Dashboard — Follower & Employee Snapshots](#10-dashboard--follower--employee-snapshots)
11. [Dashboard — News](#11-dashboard--news)
12. [Dashboard — Hiring](#12-dashboard--hiring)
13. [Dashboard — Trends](#13-dashboard--trends)
14. [Reports](#14-reports)

---

## 1. Authentication

### Register
```bash
curl -X POST http://localhost:8000/api/monitoring/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepass123",
    "password_confirm": "securepass123"
  }'
```

**Response `201`:**
```json
{
  "user": { "id": 1, "username": "john_doe", "email": "john@example.com" },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

### Login
```bash
curl -X POST http://localhost:8000/api/monitoring/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "john_doe", "password": "securepass123"}'
```

**Response `200`:**
```json
{
  "user": { "id": 1, "username": "john_doe", "email": "john@example.com" },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

### Logout
```bash
curl -X POST http://localhost:8000/api/monitoring/auth/logout/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response `200`:** `{"message": "Logged out successfully"}`

---

## 2. Competitors

### List competitors
```bash
curl http://localhost:8000/api/monitoring/competitors/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Create competitor
```bash
curl -X POST http://localhost:8000/api/monitoring/competitors/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Honda Pakistan",
    "website_base_url": "https://honda.com.pk",
    "linkedin_url": "https://www.linkedin.com/company/honda-pakistan",
    "stock_symbol": "HMC"
  }'
```

**Note:** `linkedin_url` and `stock_symbol` are optional. `stock_symbol` unlocks all financial dashboard sections.

The response includes `onboarding_status` which tracks the initial data pipeline. The frontend should poll `GET /api/monitoring/competitors/{id}/` every 5 seconds until status is `ready` or `error`.

| `onboarding_status` | Meaning | Frontend label |
|---|---|---|
| `scraping` | Playwright is scraping all website pages | "Scraping pages..." |
| `indexing` | Building ChromaDB embeddings for RAG | "Building AI index..." |
| `ready` | Pipeline complete — RAG available | *(no indicator)* |
| `error` | Pipeline failed — see `onboarding_error` | "Setup failed" |

**Important:** During `scraping` and `indexing` states, the AI assistant will not have data for this competitor yet.

---

### Get competitor
```bash
curl http://localhost:8000/api/monitoring/competitors/1/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Update competitor
```bash
curl -X PATCH http://localhost:8000/api/monitoring/competitors/1/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stock_symbol": "HMC"}'
```

---

### Delete competitor
```bash
curl -X DELETE http://localhost:8000/api/monitoring/competitors/1/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Search stock symbol (before creating competitor)
```bash
curl "http://localhost:8000/api/dashboard/search-symbol/?name=Honda&limit=10" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "query": "Honda",
  "results": [
    { "symbol": "HMC", "name": "Honda Motor Co., Ltd.", "exchange": "NYSE", "currency": "USD" }
  ]
}
```

---

## 3. Accounts — Roles & Users

### Get my permissions
```bash
curl http://localhost:8000/api/accounts/me/permissions/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "dashboard": true,
  "competitors": true,
  "ai_assistant": true,
  "reports": true,
  "settings": true,
  "alerts": true,
  "user_type": "super_admin"
}
```

---

### Create role
```bash
curl -X POST http://localhost:8000/api/accounts/roles/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Analyst"}'
```

---

### List roles
```bash
curl http://localhost:8000/api/accounts/roles/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Update role permissions
```bash
curl -X PATCH http://localhost:8000/api/accounts/roles/1/permissions/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dashboard": true,
    "competitors": true,
    "ai_assistant": false,
    "reports": true,
    "settings": false,
    "alerts": true
  }'
```

---

### Create user
```bash
curl -X POST http://localhost:8000/api/accounts/users/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "analyst1",
    "email": "analyst1@company.com",
    "password": "securepass123",
    "role_id": 1
  }'
```

---

### List users
```bash
curl http://localhost:8000/api/accounts/users/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Update user
```bash
curl -X PUT http://localhost:8000/api/accounts/users/2/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role_id": 2}'
```

---

### Delete user (soft delete)
```bash
curl -X DELETE http://localhost:8000/api/accounts/users/2/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 4. Alerts

### Get alert preference
```bash
curl http://localhost:8000/api/accounts/me/alert-preference/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "alert_email": "user@gmail.com",
  "notify_website_changes": true,
  "notify_new_jobs": true,
  "notify_follower_change": true,
  "notify_new_pages": true
}
```

---

### Update alert preference
```bash
curl -X PATCH http://localhost:8000/api/accounts/me/alert-preference/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_email": "user@gmail.com",
    "notify_website_changes": true,
    "notify_new_jobs": false,
    "notify_follower_change": true,
    "notify_new_pages": true
  }'
```

All fields are optional — send only what you want to change.
If `alert_email` is blank, no email is sent but alerts still appear in the UI.

---

### Get alerts list
```bash
# Last 7 days, all types (default)
curl "http://localhost:8000/api/accounts/me/alerts/?days=7" \
  -H "Authorization: Token YOUR_TOKEN"

# Filter by type (options: website_changes, new_pages, new_jobs, follower_change)
curl "http://localhost:8000/api/accounts/me/alerts/?days=30&type=new_jobs" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "count": 3,
  "days": 7,
  "alerts": [
    {
      "type": "website_change",
      "title": "Honda Pakistan — Website Change",
      "description": "Honda reduced the City 1.5L price by PKR 50,000.",
      "meta": { "url": "https://honda.com.pk/pricing", "change_type": "modified" },
      "competitor": "Honda Pakistan",
      "timestamp": "2026-05-12T10:00:00Z"
    }
  ]
}
```

Alert type → UI color: `website_change` red · `new_page` green · `new_job` blue · `follower_change` purple

---

### Test alert email (development only)
```bash
curl -X POST http://localhost:8000/api/accounts/me/alert-preference/test-email/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "all"}'
```

`type` options: `all`, `website_changes`, `new_pages`, `new_jobs`, `follower_change`

---

## 5. Dashboard — Overview

### Aggregate KPI counts
```bash
curl http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "total_competitors": 5,
  "web_changes_30d": 142,
  "significant_changes_30d": 18,
  "active_job_postings": 312,
  "social_posts_30d": 87,
  "high_confidence_alerts": 4
}
```

---

### Scraping health
```bash
curl http://localhost:8000/api/dashboard/scraping-health/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "period_days": 7,
  "monitoring_tasks": { "completed": 34, "failed": 2, "pending": 1, "running": 0 },
  "scraping_logs": { "success": 31, "failed": 3, "partial": 1 }
}
```

---

## 6. Dashboard — Financial Profile

> Requires `stock_symbol` set on the competitor. Returns `{"available": false}` if not set.

### Company profile card
```bash
curl http://localhost:8000/api/dashboard/financial-profile/1/profile/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Historical market cap
```bash
curl "http://localhost:8000/api/dashboard/financial-profile/1/market-cap/?years=5" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Employee count over time
```bash
curl http://localhost:8000/api/dashboard/financial-profile/1/employee-count/ \
  -H "Authorization: Token YOUR_TOKEN"
```

Returns both `fmp_series` (annual SEC filings) and `db_series` (LinkedIn snapshots).

---

### Executive team
```bash
curl http://localhost:8000/api/dashboard/financial-profile/1/executives/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 7. Dashboard — Financial Health

### Annual income statement
```bash
curl "http://localhost:8000/api/dashboard/financial-health/1/income/?years=5" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Year-over-year growth rates
```bash
curl http://localhost:8000/api/dashboard/financial-health/1/growth/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Financial ratios
```bash
curl http://localhost:8000/api/dashboard/financial-health/1/ratios/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Financial health rating
```bash
curl http://localhost:8000/api/dashboard/financial-health/1/rating/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "available": true,
  "rating": "B+",
  "rating_score": 3.8,
  "recommendation": "Buy",
  "sub_scores": { "roe_score": 5, "roa_score": 4, "debt_to_equity_score": 3 }
}
```

Rating scale: `A` → `B+` → `B` → `C+` → `C`

---

### Revenue per employee
```bash
curl http://localhost:8000/api/dashboard/financial-health/1/revenue-per-employee/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 8. Dashboard — Website Changes

### Daily change heatmap
```bash
curl "http://localhost:8000/api/dashboard/website-changes/heatmap/?days=90&competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Change type breakdown (added / removed / modified)
```bash
curl "http://localhost:8000/api/dashboard/website-changes/type-breakdown/?competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Significant vs minor changes by week
```bash
curl "http://localhost:8000/api/dashboard/website-changes/significance-trend/?weeks=12&competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Changes ranked by competitor
```bash
curl "http://localhost:8000/api/dashboard/website-changes/per-competitor/?days=30" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Activity feed with LLM summaries
```bash
curl "http://localhost:8000/api/dashboard/website-changes/feed/?competitor_id=1&page=1&limit=20" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### 7-day rolling change velocity
```bash
curl "http://localhost:8000/api/dashboard/website-changes/velocity/?days=60&competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 9. Dashboard — Social Media Posts

### Total engagement per competitor
```bash
curl "http://localhost:8000/api/dashboard/social-posts/engagement/?days=30" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Post volume by week and platform
```bash
curl "http://localhost:8000/api/dashboard/social-posts/volume-trend/?weeks=12&competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Post type distribution
```bash
curl "http://localhost:8000/api/dashboard/social-posts/type-distribution/?competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Top posts by engagement
```bash
curl "http://localhost:8000/api/dashboard/social-posts/top-posts/?days=30&limit=10&competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Posting frequency heatmap (day × hour)
```bash
curl "http://localhost:8000/api/dashboard/social-posts/frequency-heatmap/?competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Author leaderboard
```bash
curl "http://localhost:8000/api/dashboard/social-posts/authors/?competitor_id=1&limit=10" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 10. Dashboard — Follower & Employee Snapshots

### Follower growth over time
```bash
curl "http://localhost:8000/api/dashboard/snapshots/follower-growth/?competitor_id=1&platform=linkedin&months=6" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Month-over-month growth rate for all competitors
```bash
curl "http://localhost:8000/api/dashboard/snapshots/growth-rate/?platform=linkedin" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Follower count per platform (grouped bar)
```bash
curl http://localhost:8000/api/dashboard/snapshots/platform-comparison/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Followers ÷ employees ratio
```bash
curl http://localhost:8000/api/dashboard/snapshots/follower-employee-ratio/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 11. Dashboard — News

### News feed (all competitors)
```bash
# Last 6 days (default)
curl http://localhost:8000/api/dashboard/news/feed/ \
  -H "Authorization: Token YOUR_TOKEN"

# Custom range and page
curl "http://localhost:8000/api/dashboard/news/feed/?days=3&page=2" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "days": 6,
  "total": 14,
  "page": 1,
  "page_size": 20,
  "articles": [
    {
      "title": "Honda Pakistan Recalls Thousands of Cars",
      "source": "ProPakistani",
      "url": "https://propakistani.pk/...",
      "published_at": "2026-05-15T10:00:00Z",
      "competitor_name": "Honda Pakistan"
    }
  ]
}
```

---

### News correlation with website changes (per competitor)
```bash
curl "http://localhost:8000/api/dashboard/news/1/correlation/?days=30" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 12. Dashboard — Hiring

### Active job openings per competitor
```bash
curl http://localhost:8000/api/dashboard/hiring/active-openings/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Weekly hiring trend
```bash
curl "http://localhost:8000/api/dashboard/hiring/trend/?weeks=12&competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Job function breakdown
```bash
curl "http://localhost:8000/api/dashboard/hiring/function-breakdown/?competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Seniority breakdown
```bash
curl "http://localhost:8000/api/dashboard/hiring/seniority/?competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Top hiring locations
```bash
curl "http://localhost:8000/api/dashboard/hiring/locations/?competitor_id=1&limit=10" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### New vs closed postings
```bash
curl "http://localhost:8000/api/dashboard/hiring/new-vs-closed/?months=3" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "period_months": 3,
  "new_jobs": 187,
  "closed_jobs": 134,
  "ratio": 1.4,
  "signal": "growing"
}
```

`signal` values: `growing` (ratio > 1.2) · `stable` (0.8–1.2) · `consolidating` (< 0.8)

---

### Employment type breakdown
```bash
curl "http://localhost:8000/api/dashboard/hiring/employment-type/?competitor_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 13. Dashboard — Trends

### Trend direction summary (all competitors)
```bash
curl http://localhost:8000/api/dashboard/trends/direction-summary/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Metric time series
```bash
curl "http://localhost:8000/api/dashboard/trends/metric-series/?competitor_id=1&metric_type=engagement_score&months=6" \
  -H "Authorization: Token YOUR_TOKEN"
```

Available `metric_type` values are returned in the `available_metrics` field of the response.

---

### Confidence table (all trends)
```bash
# All trends
curl http://localhost:8000/api/dashboard/trends/confidence-table/ \
  -H "Authorization: Token YOUR_TOKEN"

# High-confidence only
curl "http://localhost:8000/api/dashboard/trends/confidence-table/?min_confidence=0.8" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### High-confidence trend alerts
```bash
curl http://localhost:8000/api/dashboard/trends/alerts/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Trend period coverage (Gantt timeline)
```bash
curl http://localhost:8000/api/dashboard/trends/coverage/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

## 14. Reports

### Generate report
```bash
curl -X POST http://localhost:8000/api/reports/generate/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q4 Competitive Analysis",
    "report_type": "executive",
    "period_start": "2026-04-10",
    "period_end": "2026-05-10",
    "competitor_ids": []
  }'
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | Yes | Report title |
| `report_type` | string | Yes | `executive` or `analyst` |
| `period_start` | string | Yes | `YYYY-MM-DD` |
| `period_end` | string | Yes | `YYYY-MM-DD` — max 30 days after start, cannot be future |
| `competitor_ids` | array | Yes | Specific IDs, or `[]` for all competitors |

**Response `202`:**
```json
{ "report_id": 8, "status": "pending" }
```

> Celery worker must be running for report generation to proceed.

---

### Check report status
```bash
curl http://localhost:8000/api/reports/8/ \
  -H "Authorization: Token YOUR_TOKEN"
```

Poll every 3 seconds until `status` is `completed` or `failed`.

Status values: `pending` · `generating` · `completed` · `failed`

---

### Download report as PDF
```bash
curl http://localhost:8000/api/reports/8/pdf/ \
  -H "Authorization: Token YOUR_TOKEN" \
  --output report.pdf
```

Only call when `status == "completed"`. Returns a PDF file.

---

### List reports
```bash
# All reports
curl http://localhost:8000/api/reports/ \
  -H "Authorization: Token YOUR_TOKEN"

# Filter by type
curl "http://localhost:8000/api/reports/?type=executive" \
  -H "Authorization: Token YOUR_TOKEN"

# Filter by period (reports created in last N days)
curl "http://localhost:8000/api/reports/?period=30" \
  -H "Authorization: Token YOUR_TOKEN"

# Search by title
curl "http://localhost:8000/api/reports/?search=Q4" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### Delete report
```bash
curl -X DELETE http://localhost:8000/api/reports/8/delete/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response `204 No Content`**

---

## Quick Reference

| # | Method | Endpoint | Description |
|---|---|---|---|
| — | POST | `/api/monitoring/auth/register/` | Register |
| — | POST | `/api/monitoring/auth/login/` | Login |
| — | POST | `/api/monitoring/auth/logout/` | Logout |
| — | GET | `/api/accounts/me/permissions/` | My page permissions |
| — | GET/PATCH | `/api/accounts/me/alert-preference/` | Alert email settings |
| — | GET | `/api/accounts/me/alerts/` | Alerts list |
| — | POST | `/api/monitoring/competitors/` | Create competitor |
| — | GET | `/api/monitoring/competitors/` | List competitors |
| — | PATCH | `/api/monitoring/competitors/{id}/` | Update competitor |
| — | GET | `/api/dashboard/search-symbol/` | Search stock symbol |
| — | GET | `/api/dashboard/overview/` | Dashboard KPIs |
| — | GET | `/api/dashboard/scraping-health/` | Scraping task health |
| 1.1 | GET | `/api/dashboard/financial-profile/{id}/profile/` | Company profile |
| 1.2 | GET | `/api/dashboard/financial-profile/{id}/market-cap/` | Market cap history |
| 1.3 | GET | `/api/dashboard/financial-profile/{id}/employee-count/` | Employee count |
| 1.4 | GET | `/api/dashboard/financial-profile/{id}/executives/` | Executive team |
| 2.1 | GET | `/api/dashboard/financial-health/{id}/income/` | Income statement |
| 2.2 | GET | `/api/dashboard/financial-health/{id}/growth/` | Growth rates |
| 2.3 | GET | `/api/dashboard/financial-health/{id}/ratios/` | Financial ratios |
| 2.4 | GET | `/api/dashboard/financial-health/{id}/rating/` | Health rating |
| 2.5 | GET | `/api/dashboard/financial-health/{id}/revenue-per-employee/` | Revenue per employee |
| 3.1 | GET | `/api/dashboard/website-changes/heatmap/` | Change heatmap |
| 3.2 | GET | `/api/dashboard/website-changes/type-breakdown/` | Change types |
| 3.3 | GET | `/api/dashboard/website-changes/significance-trend/` | Significance trend |
| 3.4 | GET | `/api/dashboard/website-changes/per-competitor/` | Changes per competitor |
| 3.5 | GET | `/api/dashboard/website-changes/feed/` | Activity feed |
| 3.6 | GET | `/api/dashboard/website-changes/velocity/` | Change velocity |
| 4.1 | GET | `/api/dashboard/social-posts/engagement/` | Engagement totals |
| 4.2 | GET | `/api/dashboard/social-posts/volume-trend/` | Post volume by week |
| 4.3 | GET | `/api/dashboard/social-posts/type-distribution/` | Post types |
| 4.4 | GET | `/api/dashboard/social-posts/top-posts/` | Top posts |
| 4.5 | GET | `/api/dashboard/social-posts/frequency-heatmap/` | Posting frequency |
| 4.6 | GET | `/api/dashboard/social-posts/authors/` | Author leaderboard |
| 5.1 | GET | `/api/dashboard/snapshots/follower-growth/` | Follower growth |
| 5.2 | GET | `/api/dashboard/snapshots/growth-rate/` | Growth rate |
| 5.3 | GET | `/api/dashboard/snapshots/platform-comparison/` | Platform comparison |
| 5.4 | GET | `/api/dashboard/snapshots/follower-employee-ratio/` | Follower/employee ratio |
| 6.1 | GET | `/api/dashboard/news/feed/` | News feed |
| 6.2 | GET | `/api/dashboard/news/{id}/correlation/` | News correlation |
| 7.1 | GET | `/api/dashboard/hiring/active-openings/` | Active jobs |
| 7.2 | GET | `/api/dashboard/hiring/trend/` | Hiring trend |
| 7.3 | GET | `/api/dashboard/hiring/function-breakdown/` | Job functions |
| 7.4 | GET | `/api/dashboard/hiring/seniority/` | Seniority levels |
| 7.5 | GET | `/api/dashboard/hiring/locations/` | Hiring locations |
| 7.6 | GET | `/api/dashboard/hiring/new-vs-closed/` | New vs closed jobs |
| 7.7 | GET | `/api/dashboard/hiring/employment-type/` | Employment types |
| 8.1 | GET | `/api/dashboard/trends/direction-summary/` | Trend summary |
| 8.2 | GET | `/api/dashboard/trends/metric-series/` | Metric time series |
| 8.3 | GET | `/api/dashboard/trends/confidence-table/` | Confidence table |
| 8.4 | GET | `/api/dashboard/trends/alerts/` | Trend alerts |
| 8.5 | GET | `/api/dashboard/trends/coverage/` | Trend coverage |
| — | POST | `/api/reports/generate/` | Generate report |
| — | GET | `/api/reports/{id}/` | Report status |
| — | GET | `/api/reports/{id}/pdf/` | Download PDF |
| — | GET | `/api/reports/` | List reports |
| — | DELETE | `/api/reports/{id}/delete/` | Delete report |
