# Apify Actors — LinkedIn Scraping

This document covers the three Apify actors used for LinkedIn scraping, their pricing, input/output formats, and how they fit into the scraping pipeline.

---

## Overview

| Purpose | Actor | Apify ID | Pricing Model |
|---|---|---|---|
| Company snapshot | automation-lab/linkedin-company-scraper | `automation-lab~linkedin-company-scraper` | Pay-per-result — $0.003/company |
| Posts | harvestapi/linkedin-profile-posts | `harvestapi~linkedin-profile-posts` | Pay-per-result — $1.50/1,000 posts |
| Jobs | valig/linkedin-jobs-scraper | `valig~linkedin-jobs-scraper` | Pay-per-result — $0.40/1,000 jobs |

All three actors use **pay-per-result pricing** — no monthly rental fee. Costs are deducted directly from your Apify platform credits ($5/month on the free plan).

---

## Free Plan Budget Estimates

With the free $5/month Apify credit:

| Actor | Cost per unit | Units you get for $5 |
|---|---|---|
| Company scraper | ~$0.003/company + $0.005/run | ~1,400 company profiles |
| Posts scraper | $1.50/1,000 posts | ~3,300 posts |
| Jobs scraper | $0.40/1,000 jobs | ~12,000 job listings |

For a typical setup with 2–5 competitors running daily, the free plan is sufficient.

---

## Actor 1 — Company Snapshot

**Apify page**: apify.com/automation-lab/linkedin-company-scraper

**What it scrapes**: Follower count, employee count, company info (name, industry, website, headquarters). Does **not** return posts.

**Input**:
```json
{
  "companyUrls": ["https://www.linkedin.com/company/honda-pakistan-official/"],
  "maxCompanies": 1
}
```

**Key output fields**:
| Field | Description |
|---|---|
| `followerCount` | Number of LinkedIn followers |
| `employeeCount` | Number of listed employees |
| `name` | Company name |
| `industry` | Industry category |
| `website` | Company website URL |

**Saved to**: `SocialMediaSnapshot` model (one record per competitor per day)

---

## Actor 2 — Posts

**Apify page**: apify.com/harvestapi/linkedin-profile-posts

**What it scrapes**: Posts from a company or profile page, filtered by date. Supports both company pages (`/company/`) and personal profiles (`/in/`).

**Input**:
```json
{
  "targetUrls": ["https://www.linkedin.com/company/honda-pakistan-official/"],
  "postedLimitDate": "2026-05-29",
  "maxPosts": 50,
  "scrapeReactions": false,
  "scrapeComments": false
}
```

- `postedLimitDate` — only fetch posts on or after this date (ISO date string `YYYY-MM-DD`)
- `maxPosts` — hard cap on posts returned per run (set to 50 to control costs)
- `scrapeReactions` / `scrapeComments` — kept false to avoid extra credit usage

**Key output fields**:
| Field | Description |
|---|---|
| `id` | Unique post ID |
| `content` | Full post text |
| `linkedinUrl` | Direct URL to the post |
| `postedAt` | Object with `timestamp` and `date` |
| `engagement.likes` | Like count |
| `engagement.comments` | Comment count |
| `engagement.shares` | Share count |
| `author.name` | Author's full name |
| `author.info` | Author's headline/position |

**Saved to**: `SocialMediaPost` model

**Date logic** (to avoid scraping full history):
- First run (no existing posts in DB): fetches posts from today only
- Daily cron runs: fetches posts from yesterday only
- Manual override: use `--days-back N` flag on the management command

---

## Actor 3 — Jobs

**Apify page**: apify.com/valig/linkedin-jobs-scraper

**What it scrapes**: Job listings posted by a company in the last 7 days, searched by company name.

**Input**:
```json
{
  "companyName": ["Honda"],
  "datePosted": "r604800",
  "limit": 50
}
```

- `datePosted: "r604800"` — LinkedIn filter code for "posted in last 7 days"
- `limit` — max results per run

**Key output fields**:
| Field | Description |
|---|---|
| `id` | Unique job ID |
| `url` | Job listing URL |
| `title` | Job title |
| `location` | Job location |
| `contractType` | Employment type (Full-time, Part-time, etc.) |
| `experienceLevel` | Seniority level |
| `description` | Full job description |
| `companyUrl` | Company LinkedIn URL (used for filtering) |
| `postedDate` | Date the job was posted |

**Saved to**: `JobPosting` model

**Deduplication logic**:
- New jobs: saved with `is_new=True`, `is_active=True`
- Existing jobs: updated `last_seen_at`, `is_new=False`
- Jobs not returned in latest scrape: marked `is_active=False`

---

## Settings

Actor IDs are configured in `config/settings.py` and can be overridden via environment variables:

```env
APIFY_API_TOKEN=your_token_here
APIFY_COMPANY_ACTOR_ID=automation-lab~linkedin-company-scraper
APIFY_POSTS_ACTOR_ID=harvestapi~linkedin-profile-posts
APIFY_JOBS_ACTOR_ID=valig~linkedin-jobs-scraper
```

Only `APIFY_API_TOKEN` is required. The actor ID env vars are optional — the defaults above are already set in `settings.py`.

---

## Switching Actors

If an actor gets deprecated or pricing changes:

1. Find the replacement actor on apify.com
2. Check its Pricing tab — confirm it is pay-per-result (not rental)
3. Check its Input and API tabs for the correct input field names
4. Update the relevant env var in `.env` and on the server
5. Update the input/output field mapping in `apps/social_media/services/apify_service.py`
