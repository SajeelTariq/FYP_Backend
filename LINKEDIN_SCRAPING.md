# LinkedIn Scraping — How It Works & How to Test

## What Was Built

A new Django app `apps/social_media/` that scrapes LinkedIn company data daily using
the **Apify** cloud scraping platform. No browser or LinkedIn session is needed on your
server — Apify handles everything on their cloud.

---

## Architecture Overview

```
Celery Beat (scheduler)
    ├── 2:00 AM daily → run_daily_monitoring()      ← existing website pipeline
    └── 3:00 AM daily → run_linkedin_monitoring()   ← NEW LinkedIn pipeline
                              │
                              └── for each competitor that has a linkedin_url
                                      │
                                      ├── Apify Actor 1: scrape company profile
                                      │       → posts (last ~30 days)
                                      │       → follower count
                                      │       → employee count
                                      │
                                      └── Apify Actor 2: scrape job listings
                                              → new jobs (is_new=True)
                                              → updated jobs
                                              → deactivated jobs (no longer live)
```

---

## Apify Actors Used

| Purpose | Actor | Actor ID | Cost |
|---|---|---|---|
| Company profile + posts | `simpleapi/linkedin-company-scraper-actor` | `meZYSFfylaaZzaCNN` | ~$0.10–0.50 per run |
| Job listings | `curious_coder/linkedin-jobs-scraper` | `hKByXkMQaC5Qt9UMN` | $1.00 per 1000 results |

Both actors work **without LinkedIn cookies** in public mode.

---

## Database Models

### `SocialMediaPost`
Stores individual LinkedIn posts scraped from a competitor's company page.
- `post_id` — LinkedIn's native ID (used for deduplication — same post is never saved twice)
- `content` — full post text
- `num_likes / num_comments / num_shares` — engagement metrics
- `posted_at` — when the post was published on LinkedIn

### `JobPosting`
Stores job listings found for a competitor.
- `job_id` — LinkedIn job ID (deduplication key)
- `is_new` — `True` only on the first run it was detected (useful for alerting)
- `is_active` — set to `False` automatically when a job no longer appears in the scrape
- `seniority_level`, `employment_type`, `job_function` — useful for filtering

### `SocialMediaSnapshot`
A daily record of follower and employee count — lets you track growth trends over time.

---

## Setup: Before You Can Run Anything

### Step 1 — Get your Apify API token
1. Go to [apify.com](https://apify.com) and create a free account
2. Go to **Settings → Integrations → API token**
3. Copy your token

### Step 2 — Paste it in `.env`
Open `.env` and replace the placeholder:
```
APIFY_API_TOKEN=your-apify-api-token-here
```

### Step 3 — Subscribe to the actors on Apify
The two actors need a one-time subscription:
1. Visit https://apify.com/simpleapi/linkedin-company-scraper-actor → click **Try for free**
2. Visit https://apify.com/curious_coder/linkedin-jobs-scraper → click **Try for free**

### Step 4 — Run migrations
```bash
python manage.py makemigrations social_media
python manage.py migrate
```

### Step 5 — Make sure your competitor has a LinkedIn URL
In Django Admin or via the API, ensure the competitor you want to test has
`linkedin_url` set (e.g. `https://www.linkedin.com/company/netflix/`).

---

## How to Test (Without Cron Jobs)

You have **three ways** to trigger a scrape manually:

---

### Option A — Management Command (Recommended for testing)

Run directly from terminal, no Celery needed:

```bash
# Dry run — see what WOULD be scraped, no Apify calls made
python manage.py run_linkedin_scraping --dry-run

# Scrape all competitors that have a LinkedIn URL
python manage.py run_linkedin_scraping

# Scrape a single competitor (replace 3 with your competitor's ID)
python manage.py run_linkedin_scraping --competitor-id 3
```

You'll see output like:
```
Found 1 competitor(s) to scrape:
  [3] Netflix — https://www.linkedin.com/company/netflix/

→ Scraping Netflix...
  ✓ Posts:    12 new / 15 total
  ✓ Jobs:     8 new, 0 updated, 0 deactivated
  ✓ Snapshot: followers=28500, employees=1200

Done.
```

---

### Option B — REST API Endpoint

If your Django server is running, use these endpoints (all require auth token header):

**Scrape a single competitor:**
```http
POST /api/social-media/trigger/{competitor_id}/scrape-linkedin/
Authorization: Token your-auth-token-here
```

**Scrape all competitors at once:**
```http
POST /api/social-media/trigger/scrape-all-linkedin/
Authorization: Token your-auth-token-here
```

Both return a `task_id` immediately (the job runs in Celery background).
The response looks like:
```json
{
  "message": "LinkedIn scrape queued for 'Netflix'.",
  "task_id": "abc123...",
  "competitor_id": 3,
  "linkedin_url": "https://www.linkedin.com/company/netflix/"
}
```

---

### Option C — Django Shell (Lowest level, good for debugging)

```python
python manage.py shell

from apps.monitoring.models import Competitor
from apps.social_media.tasks import _scrape_competitor_linkedin

comp = Competitor.objects.get(id=3)
result = _scrape_competitor_linkedin(comp)
print(result)
```

---

## Viewing the Scraped Data

### Via REST API

```http
# All LinkedIn posts for your competitors
GET /api/social-media/posts/
GET /api/social-media/posts/?competitor=3
GET /api/social-media/posts/?platform=linkedin

# Job listings
GET /api/social-media/jobs/
GET /api/social-media/jobs/?competitor=3&is_new=true
GET /api/social-media/jobs/?is_active=true

# Only newly detected jobs (since last scrape)
GET /api/social-media/jobs/new_today/

# Follower/employee count history
GET /api/social-media/snapshots/
GET /api/social-media/snapshots/?competitor=3
```

### Via Django Admin

Go to `http://localhost:8000/admin/` and you'll see:
- **Social Media → Social Media Posts**
- **Social Media → Job Postings**
- **Social Media → Social Media Snapshots**

---

## How Deduplication Works

**Posts:** Each post has a `post_id` (LinkedIn's own ID). On every scrape, we call
`get_or_create(post_id=...)` — so the same post is never inserted twice even if it
appears in multiple scrapes. The `scraped_at` timestamp reflects when we first saw it.

**Jobs:** Same approach with `job_id`. Additionally:
- If a job was seen before → `is_new` is set to `False`, `last_seen_at` is updated
- If a job was seen last time but isn't in this scrape → `is_active` is set to `False`
- If a job is brand new → saved with `is_new=True` (useful for sending alerts later)

---

## How the Jobs Search Works

The jobs scraper needs a LinkedIn Jobs search URL. We construct it from the company's
LinkedIn URL like this:

```
https://www.linkedin.com/company/netflix/
                              ↓ extract slug
                           "netflix"
                              ↓ build search URL
https://www.linkedin.com/jobs/search/?keywords=netflix&f_TPR=r604800
```

`f_TPR=r604800` = "posted in the last 7 days" — so we only pull fresh jobs each run.

After getting results from Apify, we also **filter by `companyLinkedinUrl`** in the
response to drop any jobs that happen to mention the company name but aren't actually
posted by that company.

---

## Cron Schedule (When Running Normally)

| Task | Time | File |
|---|---|---|
| Website scraping | 2:00 AM daily | `apps/scraping/tasks.py` |
| LinkedIn scraping | 3:00 AM daily | `apps/social_media/tasks.py` |

The 1-hour gap prevents the two pipelines from competing for Celery workers.

---

## Troubleshooting

**`APIFY_API_TOKEN is not set`**
→ You forgot to paste your token in `.env`

**`Actor run ended with status=FAILED`**
→ Usually means the actor hit LinkedIn's rate limit or the company URL is wrong.
  Check that the URL format is `https://www.linkedin.com/company/SLUG/` (not a personal profile).

**`No competitors with a LinkedIn URL found`**
→ Make sure you've added `linkedin_url` to at least one competitor in the database.

**Jobs results are empty or from wrong companies**
→ The slug extracted from the LinkedIn URL may not match LinkedIn's jobs index.
  Try a more specific company name in the `--competitor-id` run and check the logs.

**Actor subscription error**
→ You need to click "Try for free" on both actor pages on apify.com before the API
  will let you run them.
