# TrackRival Dashboard API Reference

Base URL: `http://localhost:8000/api/dashboard/`

---

## Authentication

All endpoints require a token in the `Authorization` header.

```
Authorization: Token <your_token>
```

Obtain a token via:

```
POST /api/monitoring/auth/login/
Body: { "username": "...", "password": "..." }
Response: { "token": "abc123..." }
```

Missing or invalid token → `401 Unauthorized`

---

## General Rules

- All data is scoped to the authenticated user's competitors only.
- Competitors without a `stock_symbol` set return `{ "available": false, "reason": "No stock symbol configured" }` on FMP endpoints — render an "Add stock symbol" prompt on those sections.
- FMP endpoints return `"stale": true` if live data is unavailable and a cached copy is being served.
- All dates are returned as `YYYY-MM-DD` strings. All datetimes are ISO 8601 UTC.
- Monetary values are in USD unless stated otherwise.

---

## Error Shapes

```json
{ "error": "Competitor not found",   "code": "NOT_FOUND" }          → 404
{ "error": "FMP API unavailable",    "code": "UPSTREAM_ERROR" }     → 503
{ "error": "Query param required",   "code": "MISSING_PARAM" }      → 400
{ "available": false, "reason": "No stock symbol configured" }      → 200
```

---

## Add Competitor Flow — Stock Symbol

When adding a competitor the frontend should let the user search for the company to auto-assign a stock symbol. This unlocks all financial data sections.

### Step 1 — Search by company name

```
GET /api/dashboard/search-symbol/?name={company_name}
```

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `name` | required | Company name to search e.g. `Apple`, `Salesforce` |
| `limit` | `10` | Max results (max 20) |

**Response**
```json
{
  "query": "Apple",
  "results": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "exchange": "NASDAQ",
      "exchange_full": "NASDAQ Global Select",
      "currency": "USD"
    },
    {
      "symbol": "APLE",
      "name": "Apple Hospitality REIT, Inc.",
      "exchange": "NYSE",
      "exchange_full": "New York Stock Exchange",
      "currency": "USD"
    }
  ]
}
```

> Results are sorted — major exchanges (NASDAQ, NYSE, LSE) appear first. Crypto and OTC listings are filtered out. If the company is private and not listed, results will be empty — that is fine, the symbol field is optional.

---

### Step 2 — Create competitor with symbol

Pass the selected symbol in the create request:

```
POST /api/monitoring/competitors/
Body:
{
  "name": "Apple Inc",
  "website_base_url": "https://www.apple.com",
  "stock_symbol": "AAPL"
}
```

---

### Step 3 — Update symbol on existing competitor

If a competitor was already created without a symbol:

```
PATCH /api/monitoring/competitors/{competitor_id}/
Body: { "stock_symbol": "AAPL" }
```

Once the symbol is saved all financial profile and health endpoints start working immediately for that competitor.

---

## Overview

### `GET /api/dashboard/overview/`

Aggregate counts for the entire dashboard. Use this to populate top-level KPI cards.

**Response**
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

### `GET /api/dashboard/scraping-health/`

Status counts for monitoring tasks and scraping logs over the last 7 days.

**Response**
```json
{
  "period_days": 7,
  "monitoring_tasks": {
    "completed": 34,
    "failed": 2,
    "pending": 1,
    "running": 0
  },
  "scraping_logs": {
    "success": 31,
    "failed": 3,
    "partial": 1
  }
}
```

---

## Section 1 — Competitor Financial Profile

> Data source: FMP API. Requires `stock_symbol` set on the competitor. Cached 7 days.
> If `stock_symbol` is missing all endpoints in this section return `{ "available": false }`.

### `GET /api/dashboard/financial-profile/{competitor_id}/profile/`

Core company identity card.

**Response**
```json
{
  "available": true,
  "competitor_id": 4,
  "competitor_name": "Apple Inc",
  "stock_symbol": "AAPL",
  "logo_url": null,
  "ceo": null,
  "headquarters": null,
  "sector": "Consumer Electronics",
  "industry": "Consumer Electronics",
  "website": "https://www.apple.com",
  "description": "Apple Inc. designs, manufactures...",
  "ipo_date": null,
  "exchange": "NASDAQ",
  "exchange_full": "NASDAQ Global Select",
  "currency": "USD",
  "market_cap": 4308095069502,
  "stale": false
}
```

---

### `GET /api/dashboard/financial-profile/{competitor_id}/market-cap/`

Historical market capitalisation downsampled to monthly data points.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `years` | `5` | How many years of history (max 10) |

**Response**
```json
{
  "available": true,
  "stock_symbol": "AAPL",
  "unit": "USD",
  "series": [
    { "date": "2024-01-31", "market_cap": 2980000000000 },
    { "date": "2024-02-29", "market_cap": 3100000000000 }
  ],
  "stale": false
}
```

---

### `GET /api/dashboard/financial-profile/{competitor_id}/employee-count/`

Employee count over time from two sources — FMP (annual SEC 10-K filings) and internal LinkedIn snapshots.

**Response**
```json
{
  "available": true,
  "fmp_series": [
    { "date": "2025-09-27", "employee_count": 166000 },
    { "date": "2024-09-28", "employee_count": 150000 }
  ],
  "db_series": [
    { "date": "2024-11-01", "employee_count": 162000 },
    { "date": "2024-10-01", "employee_count": 160000 }
  ],
  "stale": false
}
```

> `fmp_series` → annual, from SEC filings. `db_series` → scraped from LinkedIn (more frequent, may differ slightly).

---

### `GET /api/dashboard/financial-profile/{competitor_id}/executives/`

Executive team panel.

**Response**
```json
{
  "available": true,
  "executives": [
    {
      "name": "Greg Joswiak",
      "title": "Senior Vice President of Worldwide Marketing",
      "total_pay": null,
      "currency": "USD",
      "year_born": null,
      "active": true
    }
  ],
  "stale": false
}
```

---

## Section 2 — Revenue & Financial Health

> Data source: FMP API. Requires `stock_symbol`. Cached 7 days.

### `GET /api/dashboard/financial-health/{competitor_id}/income/`

Annual income statement series.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `years` | `5` | Number of annual periods |

**Response**
```json
{
  "available": true,
  "period": "annual",
  "series": [
    {
      "date": "2025-09-27",
      "revenue": 416161000000,
      "net_income": 93736000000,
      "gross_profit": 195201000000,
      "operating_income": 133100000000
    }
  ],
  "stale": false
}
```

---

### `GET /api/dashboard/financial-health/{competitor_id}/growth/`

Year-over-year growth rates as percentages.

**Response**
```json
{
  "available": true,
  "series": [
    {
      "date": "2025-09-27",
      "revenue_growth_pct": 6.43,
      "net_income_growth_pct": 19.5,
      "eps_growth_pct": 22.59,
      "free_cash_flow_growth_pct": 14.2
    }
  ],
  "stale": false
}
```

---

### `GET /api/dashboard/financial-health/{competitor_id}/ratios/`

Latest annual financial ratios.

**Response**
```json
{
  "available": true,
  "period": "2025-09-27",
  "ratios": {
    "gross_profit_margin": 0.469,
    "net_profit_margin": 0.269,
    "return_on_equity": 1.47,
    "return_on_assets": 0.242,
    "price_earnings_ratio": 31.2,
    "price_to_book_ratio": 45.8,
    "price_to_sales_ratio": 8.3,
    "debt_to_equity_ratio": 1.87,
    "current_ratio": 0.87
  },
  "stale": false
}
```

---

### `GET /api/dashboard/financial-health/{competitor_id}/rating/`

Composite financial health score.

> Score is derived on the backend from 5 key ratios (ROE, ROA, D/E, PE, net margin) since FMP's native rating endpoint requires a paid plan. The `note` field in the response explains this.

**Response**
```json
{
  "available": true,
  "rating": "B+",
  "rating_score": 3.8,
  "recommendation": "Buy",
  "sub_scores": {
    "roe_score": 5,
    "roa_score": 4,
    "debt_to_equity_score": 3,
    "pe_score": 4,
    "net_margin_score": 5
  },
  "note": "Derived score — /rating endpoint requires a higher FMP plan",
  "stale": false
}
```

Rating scale: `A` (5) → `B+` (4) → `B` (3) → `C+` (2) → `C` (1)
Recommendation: `Strong Buy` / `Buy` / `Hold` / `Underperform` / `Sell`

---

### `GET /api/dashboard/financial-health/{competitor_id}/revenue-per-employee/`

Revenue per employee calculated from both FMP and internal LinkedIn data.

**Response**
```json
{
  "available": true,
  "revenue": 416161000000,
  "revenue_date": "2025-09-27",
  "fmp_employee_count": 166000,
  "db_employee_count": 162000,
  "revenue_per_employee_fmp": 2507000,
  "revenue_per_employee_db": 2569000,
  "currency": "USD",
  "stale": false
}
```

---

## Section 3 — Website Change Detection

> Data source: Internal DB (`HTMLDifference` model). No FMP dependency.

### `GET /api/dashboard/website-changes/heatmap/`

Daily change count per competitor — use this for a calendar heatmap.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `days` | `90` | Lookback window |
| `competitor_id` | — | Filter to a single competitor |

**Response**
```json
{
  "data": [
    { "date": "2024-11-01", "competitor_id": 4, "competitor_name": "Apple Inc", "count": 7 },
    { "date": "2024-11-02", "competitor_id": 5, "competitor_name": "Samsung",   "count": 3 }
  ]
}
```

---

### `GET /api/dashboard/website-changes/type-breakdown/`

Count of added / removed / modified changes.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "breakdown": [
    { "change_type": "modified", "count": 312 },
    { "change_type": "added",    "count": 143 },
    { "change_type": "removed",  "count": 87  }
  ],
  "total": 542
}
```

---

### `GET /api/dashboard/website-changes/significance-trend/`

Significant vs minor change count per week — use for a stacked bar chart.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `weeks` | `12` | Lookback in weeks |
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "series": [
    { "week": "2024-10-07", "significant": 5,  "minor": 34 },
    { "week": "2024-10-14", "significant": 12, "minor": 28 }
  ]
}
```

---

### `GET /api/dashboard/website-changes/per-competitor/`

Ranked list of competitors by total changes in the period.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `days` | `30` | Lookback window |

**Response**
```json
{
  "competitors": [
    { "competitor_id": 4, "name": "Apple Inc", "total_changes": 87, "significant_changes": 9 },
    { "competitor_id": 5, "name": "Samsung",   "total_changes": 54, "significant_changes": 4 }
  ]
}
```

---

### `GET /api/dashboard/website-changes/feed/`

Paginated activity feed of individual change records with LLM summaries.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |
| `limit` | `20` | Items per page |
| `page` | `1` | Page number |

**Response**
```json
{
  "count": 542,
  "next": "/api/dashboard/website-changes/feed/?page=2&limit=20",
  "previous": null,
  "results": [
    {
      "id": 901,
      "competitor_id": 4,
      "competitor_name": "Apple Inc",
      "change_type": "modified",
      "is_significant": true,
      "detected_at": "2024-11-15T14:32:00Z",
      "llm_summary": "Pricing page updated — Pro tier increased by 12%."
    }
  ]
}
```

---

### `GET /api/dashboard/website-changes/velocity/`

7-day rolling change count per day — use for a trend line.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `days` | `60` | Lookback window for the series |
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "series": [
    { "date": "2024-11-01", "rolling_7d_count": 23 },
    { "date": "2024-11-02", "rolling_7d_count": 27 }
  ]
}
```

---

## Section 4 — Social Media Posts

> Data source: Internal DB (`SocialMediaPost` model).

### `GET /api/dashboard/social-posts/engagement/`

Total engagement (likes + comments + shares) per competitor.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `days` | `30` | Lookback window |

**Response**
```json
{
  "period_days": 30,
  "competitors": [
    {
      "competitor_id": 4,
      "name": "Apple Inc",
      "total_likes": 48200,
      "total_comments": 3100,
      "total_shares": 9800,
      "total_engagement": 61100
    }
  ]
}
```

---

### `GET /api/dashboard/social-posts/volume-trend/`

Post count per week broken down by platform.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `weeks` | `12` | Lookback in weeks |
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "series": [
    { "week": "2024-10-07", "platform": "linkedin", "count": 12 },
    { "week": "2024-10-07", "platform": "twitter",  "count": 34 }
  ]
}
```

---

### `GET /api/dashboard/social-posts/type-distribution/`

Distribution of post types (post / article / update / job).

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "competitor_id": "4",
  "distribution": [
    { "post_type": "post",    "count": 312 },
    { "post_type": "article", "count": 87  },
    { "post_type": "update",  "count": 43  },
    { "post_type": "job",     "count": 21  }
  ],
  "total": 463
}
```

---

### `GET /api/dashboard/social-posts/top-posts/`

Top posts ranked by total engagement.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `days` | `30` | Lookback window |
| `limit` | `10` | Max results |
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "posts": [
    {
      "id": 4412,
      "competitor_id": 4,
      "competitor_name": "Apple Inc",
      "author_name": "Tim Cook",
      "platform": "linkedin",
      "post_type": "article",
      "posted_at": "2024-11-10T09:00:00Z",
      "num_likes": 8400,
      "num_comments": 312,
      "num_shares": 1100,
      "total_engagement": 9812
    }
  ]
}
```

---

### `GET /api/dashboard/social-posts/frequency-heatmap/`

Posting frequency by day-of-week × hour-of-day — use for a heatmap grid.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "heatmap": [
    { "weekday": 2, "weekday_label": "Monday",    "hour": 9,  "count": 34 },
    { "weekday": 4, "weekday_label": "Wednesday", "hour": 14, "count": 58 }
  ]
}
```

> `weekday` follows Django's `ExtractWeekDay`: 1 = Sunday, 2 = Monday … 7 = Saturday.

---

### `GET /api/dashboard/social-posts/authors/`

Author leaderboard by total engagement.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |
| `limit` | `10` | Max results |

**Response**
```json
{
  "authors": [
    { "author_name": "Tim Cook",       "post_count": 48,  "total_engagement": 142300 },
    { "author_name": "Apple Newsroom", "post_count": 134, "total_engagement": 89200  }
  ]
}
```

---

## Section 5 — Follower & Employee Snapshots

> Data source: Internal DB (`SocialMediaSnapshot` model).

### `GET /api/dashboard/snapshots/follower-growth/`

Follower count time series for a competitor on a given platform.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |
| `platform` | — | `linkedin` or `twitter` |
| `months` | `6` | Lookback in months |

**Response**
```json
{
  "competitor_id": "4",
  "platform": "linkedin",
  "series": [
    { "date": "2024-05-01", "follower_count": 3100000 },
    { "date": "2024-06-01", "follower_count": 3180000 }
  ]
}
```

---

### `GET /api/dashboard/snapshots/growth-rate/`

Month-over-month follower growth % for all competitors on a platform.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `platform` | `linkedin` | `linkedin` or `twitter` |

**Response**
```json
{
  "platform": "linkedin",
  "competitors": [
    {
      "competitor_id": 4,
      "name": "Apple Inc",
      "current_followers": 3250000,
      "previous_followers": 3100000,
      "growth_pct": 4.84,
      "direction": "up"
    },
    {
      "competitor_id": 5,
      "name": "Samsung",
      "current_followers": 1820000,
      "previous_followers": 1830000,
      "growth_pct": -0.55,
      "direction": "down"
    }
  ]
}
```

---

### `GET /api/dashboard/snapshots/platform-comparison/`

Latest follower count per platform for every competitor — use for a grouped bar chart.

**Response**
```json
{
  "competitors": [
    {
      "competitor_id": 4,
      "name": "Apple Inc",
      "platforms": {
        "linkedin": 3250000,
        "twitter": 14200000
      }
    }
  ]
}
```

---

### `GET /api/dashboard/snapshots/follower-employee-ratio/`

Followers ÷ employees ratio — ranked descending.

**Response**
```json
{
  "competitors": [
    {
      "competitor_id": 4,
      "name": "Apple Inc",
      "follower_count": 3250000,
      "employee_count": 166000,
      "ratio": 19.58
    }
  ]
}
```

---

## Section 6 — News Correlation

> News feed, sentiment, and press release endpoints require a paid FMP plan and have been removed.
> The correlation endpoint works fully from the internal DB. FMP news is added as a best-effort overlay — if unavailable `news_available` will be `false` and `news_articles` will be empty arrays.

### `GET /api/dashboard/news/{competitor_id}/correlation/`

Timeline merging website changes (DB) with news articles (FMP, best-effort).

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `days` | `60` | Lookback window |

**Response**
```json
{
  "available": true,
  "news_available": false,
  "competitor_id": 4,
  "stock_symbol": "AAPL",
  "timeline": [
    {
      "date": "2024-11-15",
      "web_changes": [
        {
          "change_type": "modified",
          "is_significant": true,
          "summary": "Pricing page updated — Pro tier increased."
        }
      ],
      "news_articles": [],
      "correlated": false
    }
  ]
}
```

> `correlated: true` only fires when a **significant** web change and a news article exist on the same date.

---

## Section 7 — Job Postings & Hiring Signals

> Data source: Internal DB (`JobPosting` model).

### `GET /api/dashboard/hiring/active-openings/`

Current active job count per competitor.

**Response**
```json
{
  "total_active": 312,
  "competitors": [
    { "competitor_id": 4, "name": "Apple Inc", "active_openings": 134 },
    { "competitor_id": 5, "name": "Samsung",   "active_openings": 87  }
  ]
}
```

---

### `GET /api/dashboard/hiring/trend/`

Weekly hiring trend — new postings and total per week.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `weeks` | `12` | Lookback in weeks |
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "series": [
    {
      "week": "2024-10-07",
      "competitor_id": 4,
      "name": "Apple Inc",
      "new_postings": 23,
      "total": 45
    }
  ]
}
```

---

### `GET /api/dashboard/hiring/function-breakdown/`

Active job count by job function (Engineering, Sales, Marketing, etc.).

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "breakdown": [
    { "job_function": "Engineering", "count": 67 },
    { "job_function": "Sales",       "count": 34 },
    { "job_function": "Marketing",   "count": 18 }
  ]
}
```

---

### `GET /api/dashboard/hiring/seniority/`

Active job count by seniority level.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "breakdown": [
    { "seniority_level": "Senior",     "count": 54 },
    { "seniority_level": "Mid-Senior", "count": 38 },
    { "seniority_level": "Entry",      "count": 22 },
    { "seniority_level": "Director",   "count": 12 },
    { "seniority_level": "Executive",  "count": 8  }
  ]
}
```

---

### `GET /api/dashboard/hiring/locations/`

Top hiring locations by active job count.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |
| `limit` | `10` | Max results |

**Response**
```json
{
  "locations": [
    { "location": "Remote",            "count": 61 },
    { "location": "San Francisco, CA", "count": 43 },
    { "location": "New York, NY",      "count": 28 }
  ]
}
```

---

### `GET /api/dashboard/hiring/new-vs-closed/`

New postings vs closed postings with a hiring signal.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `months` | `3` | Lookback in months |

**Response**
```json
{
  "period_months": 3,
  "new_jobs": 187,
  "closed_jobs": 134,
  "ratio": 1.4,
  "signal": "growing"
}
```

> `signal` values: `"growing"` (ratio > 1.2) · `"stable"` (0.8–1.2) · `"consolidating"` (< 0.8)

---

### `GET /api/dashboard/hiring/employment-type/`

Active job count by employment type.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |

**Response**
```json
{
  "breakdown": [
    { "employment_type": "Full-time", "count": 112 },
    { "employment_type": "Contract",  "count": 14  },
    { "employment_type": "Part-time", "count": 8   }
  ]
}
```

---

## Section 8 — Metrics & Trend Analysis

> Data source: Internal DB (`CompetitorMetrics` and `TrendAnalysis` models).

### `GET /api/dashboard/trends/direction-summary/`

Count of all trends by direction across all competitors.

**Response**
```json
{
  "summary": [
    { "direction": "up",     "count": 8 },
    { "direction": "down",   "count": 3 },
    { "direction": "stable", "count": 5 }
  ],
  "total": 16
}
```

---

### `GET /api/dashboard/trends/metric-series/`

Time series for a specific metric type. Also returns available metric types for a dropdown.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `competitor_id` | — | Optional filter |
| `metric_type` | — | e.g. `engagement_score`, `hiring_velocity` |
| `months` | `6` | Lookback in months |

**Response**
```json
{
  "competitor_id": "4",
  "metric_type": "engagement_score",
  "available_metrics": ["engagement_score", "share_of_voice", "hiring_velocity"],
  "series": [
    { "date": "2024-05-01", "value": 72.4 },
    { "date": "2024-06-01", "value": 78.1 }
  ]
}
```

---

### `GET /api/dashboard/trends/confidence-table/`

All trend analysis records with a confidence label. Use for a sortable table.

**Query params**

| Param | Default | Description |
|-------|---------|-------------|
| `min_confidence` | `0.0` | Filter floor — use `0.8` for high-confidence only |

**Response**
```json
{
  "trends": [
    {
      "competitor_id": 4,
      "competitor_name": "Apple Inc",
      "trend_type": "hiring_velocity",
      "trend_direction": "up",
      "confidence_score": 0.94,
      "period_start": "2024-08-01",
      "period_end": "2024-11-01",
      "confidence_label": "high"
    }
  ]
}
```

> `confidence_label`: `"high"` ≥ 0.8 · `"medium"` 0.5–0.8 · `"low"` < 0.5

---

### `GET /api/dashboard/trends/alerts/`

High-confidence (≥ 0.8) upward or downward trends as actionable alerts. Use for a notification panel.

**Response**
```json
{
  "alerts": [
    {
      "competitor_id": 5,
      "competitor_name": "Samsung",
      "trend_type": "website_change_frequency",
      "trend_direction": "up",
      "confidence_score": 0.91,
      "period_start": "2024-09-01",
      "period_end": "2024-11-01",
      "alert_label": "Samsung website change frequency surging with high confidence"
    }
  ]
}
```

---

### `GET /api/dashboard/trends/coverage/`

All trend periods per competitor — use for a Gantt-style timeline chart.

**Response**
```json
{
  "coverage": [
    {
      "competitor_id": 4,
      "competitor_name": "Apple Inc",
      "trend_type": "hiring_velocity",
      "period_start": "2024-08-01",
      "period_end": "2024-11-01",
      "trend_direction": "up"
    }
  ]
}
```

---

## Quick Reference

| # | Endpoint | Source | Key Params |
|---|----------|--------|------------|
| — | `GET /search-symbol/` | FMP | `name` (required), `limit` |
| — | `GET /overview/` | DB | — |
| — | `GET /scraping-health/` | DB | — |
| 1.1 | `GET /financial-profile/{id}/profile/` | FMP | — |
| 1.2 | `GET /financial-profile/{id}/market-cap/` | FMP | `years` |
| 1.3 | `GET /financial-profile/{id}/employee-count/` | FMP + DB | — |
| 1.4 | `GET /financial-profile/{id}/executives/` | FMP | — |
| 2.1 | `GET /financial-health/{id}/income/` | FMP | `years` |
| 2.2 | `GET /financial-health/{id}/growth/` | FMP | — |
| 2.3 | `GET /financial-health/{id}/ratios/` | FMP | — |
| 2.4 | `GET /financial-health/{id}/rating/` | FMP (derived) | — |
| 2.5 | `GET /financial-health/{id}/revenue-per-employee/` | FMP + DB | — |
| 3.1 | `GET /website-changes/heatmap/` | DB | `days`, `competitor_id` |
| 3.2 | `GET /website-changes/type-breakdown/` | DB | `competitor_id` |
| 3.3 | `GET /website-changes/significance-trend/` | DB | `weeks`, `competitor_id` |
| 3.4 | `GET /website-changes/per-competitor/` | DB | `days` |
| 3.5 | `GET /website-changes/feed/` | DB | `competitor_id`, `page`, `limit` |
| 3.6 | `GET /website-changes/velocity/` | DB | `days`, `competitor_id` |
| 4.1 | `GET /social-posts/engagement/` | DB | `days` |
| 4.2 | `GET /social-posts/volume-trend/` | DB | `weeks`, `competitor_id` |
| 4.3 | `GET /social-posts/type-distribution/` | DB | `competitor_id` |
| 4.4 | `GET /social-posts/top-posts/` | DB | `days`, `limit`, `competitor_id` |
| 4.5 | `GET /social-posts/frequency-heatmap/` | DB | `competitor_id` |
| 4.6 | `GET /social-posts/authors/` | DB | `competitor_id`, `limit` |
| 5.1 | `GET /snapshots/follower-growth/` | DB | `competitor_id`, `platform`, `months` |
| 5.2 | `GET /snapshots/growth-rate/` | DB | `platform` |
| 5.3 | `GET /snapshots/platform-comparison/` | DB | — |
| 5.4 | `GET /snapshots/follower-employee-ratio/` | DB | — |
| 6.5 | `GET /news/{id}/correlation/` | DB + FMP | `days` |
| 7.1 | `GET /hiring/active-openings/` | DB | — |
| 7.2 | `GET /hiring/trend/` | DB | `weeks`, `competitor_id` |
| 7.3 | `GET /hiring/function-breakdown/` | DB | `competitor_id` |
| 7.4 | `GET /hiring/seniority/` | DB | `competitor_id` |
| 7.5 | `GET /hiring/locations/` | DB | `competitor_id`, `limit` |
| 7.6 | `GET /hiring/new-vs-closed/` | DB | `months` |
| 7.7 | `GET /hiring/employment-type/` | DB | `competitor_id` |
| 8.1 | `GET /trends/direction-summary/` | DB | — |
| 8.2 | `GET /trends/metric-series/` | DB | `competitor_id`, `metric_type`, `months` |
| 8.3 | `GET /trends/confidence-table/` | DB | `min_confidence` |
| 8.4 | `GET /trends/alerts/` | DB | — |
| 8.5 | `GET /trends/coverage/` | DB | — |
