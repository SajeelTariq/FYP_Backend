# Competitor Monitoring Backend - Setup Guide

## Overview

Your Django backend now integrates all three scraping scripts:

1. **Links_extractor.py** → `extract_competitor_links()` task
2. **Scrape_HTML.py** → `scrape_competitor_html()` task
3. **json_of_html.py** → `extract_competitor_metadata()` task

All data is stored in **PostgreSQL database** instead of text/HTML/JSON files.

---

## What's Been Integrated

### ✅ Celery Tasks Created (`apps/scraping/tasks.py`)

1. **`extract_competitor_links(competitor_id)`**

   - Uses Firecrawl API to extract all subpage URLs
   - Stores in `ExtractedLinks` model (replaces .txt files)
   - Validates website existence before scraping

2. **`scrape_competitor_html(competitor_id, use_filtered_links=False)`**

   - Uses Playwright (headless Chrome) to scrape HTML
   - Removes CSS and inline styles (same cleaning as your script)
   - Stores in `CompetitorHTML` model (replaces .html files)

3. **`extract_competitor_metadata(competitor_id)`**

   - Extracts clean text from HTML using BeautifulSoup
   - Removes duplicates and non-visible content
   - Stores in `CompetitorMetadata` model (replaces .json files)

4. **`run_full_scraping_pipeline(competitor_id, use_filtered_links=False)`**
   - Runs all three steps in sequence automatically

### ✅ API Endpoints Added (`apps/monitoring/views.py`)

- `POST /api/monitoring/competitors/{id}/extract_links/`
- `POST /api/monitoring/competitors/{id}/scrape_html/`
- `POST /api/monitoring/competitors/{id}/extract_metadata/`
- `POST /api/monitoring/competitors/{id}/run_full_pipeline/`

### ✅ Configuration

- `.env` file created with your Firecrawl API key
- `settings.py` updated to load `FIRECRAWL_API_KEY`

---

## Setup Instructions

### 1. Install Dependencies

Your dependencies are already installed! The requirements include:

- Playwright (for browser automation)
- BeautifulSoup4 (for HTML parsing)
- Requests (for Firecrawl API)

But you need to install Playwright browsers:

```powershell
python -m playwright install chromium
```

### 2. Setup Database

Make sure PostgreSQL is running (via Docker or local install), then:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 3. Start Celery Worker

Open a **new terminal** and run:

```powershell
celery -A config worker --loglevel=info --pool=solo
```

> **Note:** Use `--pool=solo` on Windows. On Linux/Mac, you can omit it.

### 4. Start Django Server

In your original terminal:

```powershell
python manage.py runserver
```

---

## How to Use

### Option 1: Full Automated Pipeline (Recommended)

```python
import requests

BASE_URL = "http://localhost:8000/api/monitoring"

# Login
response = requests.post(f"{BASE_URL}/auth/login/", json={
    "username": "your_username",
    "password": "your_password"
})
token = response.json()['token']
headers = {"Authorization": f"Token {token}"}

# Add competitor
response = requests.post(f"{BASE_URL}/competitors/",
    headers=headers,
    json={
        "name": "Kia Lucky Motor",
        "website_base_url": "https://kia-luckymotorcorp.com"
    }
)
competitor_id = response.json()['competitor']['id']

# Run full pipeline - it will automatically:
# 1. Extract links using Firecrawl
# 2. Scrape HTML using Playwright
# 3. Extract metadata for RAG
response = requests.post(
    f"{BASE_URL}/competitors/{competitor_id}/run_full_pipeline/",
    headers=headers
)
print(response.json())
# {'status': 'Task started', 'task_id': '...', 'competitor': 'Kia Lucky Motor'}
```

### Option 2: Run Individual Steps

```python
# Step 1: Extract links only
requests.post(f"{BASE_URL}/competitors/{competitor_id}/extract_links/", headers=headers)

# Step 2: Scrape HTML only (after links extracted)
requests.post(
    f"{BASE_URL}/competitors/{competitor_id}/scrape_html/",
    headers=headers,
    json={"use_filtered_links": False}
)

# Step 3: Extract metadata only (after HTML scraped)
requests.post(f"{BASE_URL}/competitors/{competitor_id}/extract_metadata/", headers=headers)
```

### Option 3: Retrieve Scraped Data

```python
# Get extracted links
links = requests.get(f"{BASE_URL}/extracted-links/?competitor={competitor_id}", headers=headers)
print(links.json())

# Get scraped HTML
html = requests.get(f"{BASE_URL}/html-content/?competitor={competitor_id}", headers=headers)
print(f"Total pages: {len(html.json())}")

# Get metadata for RAG
metadata = requests.get(f"{BASE_URL}/metadata/?competitor={competitor_id}", headers=headers)
print(metadata.json())
```

---

## Database Structure

Your data is now stored in PostgreSQL:

| Table                 | Description                            | What It Replaces           |
| --------------------- | -------------------------------------- | -------------------------- |
| `competitor`          | Competitor info with social media URLs | N/A                        |
| `extracted_links`     | All subpage URLs from website          | `initial_links_txt/*.txt`  |
| `filtered_links`      | Manually filtered URLs                 | `filtered_links_txt/*.txt` |
| `competitor_html`     | Scraped HTML content (cleaned)         | `raw_html/*/*.html`        |
| `competitor_metadata` | Clean text + metadata for RAG          | `json_of_html/*/*.json`    |

---

## Key Differences from Your Original Scripts

### Before (File-based)

```python
# Links saved to D:\FYP\backend\data\initial_links_txt\domain.txt
with open(output_file, "w") as f:
    for url in urls:
        f.write(url + "\n")
```

### After (Database-based)

```python
# Links saved to PostgreSQL
ExtractedLinks.objects.update_or_create(
    competitor=competitor,
    defaults={'links': urls}  # JSON field
)
```

### Benefits

- ✅ No file management needed
- ✅ User-specific data isolation (each user sees only their competitors)
- ✅ Easy to query and filter data
- ✅ Automatic relationship management
- ✅ Ready for RAG system integration

---

## Monitoring Task Progress

Tasks run asynchronously. You can check Celery worker logs:

```
[2025-11-16 10:00:00,123: INFO] ✅ Extracted 150 links for Honda Pakistan
[2025-11-16 10:02:30,456: INFO] 🌐 Scraping: https://honda.com.pk/about
[2025-11-16 10:02:35,789: INFO] ✅ Saved HTML for: https://honda.com.pk/about
[2025-11-16 10:05:00,012: INFO] ✅ Processed metadata for: https://honda.com.pk/about
```

---

## Next Steps

1. ✅ **Test the pipeline** with a small website first
2. ✅ **Add filtering logic** for `FilteredLinks` (currently manual)
3. ⏳ **Integrate RAG system** using `CompetitorMetadata` table
4. ⏳ **Add scheduled scraping** (daily/weekly via Celery Beat)
5. ⏳ **Connect to React frontend**

---

## Troubleshooting

### Playwright not found

```powershell
python -m playwright install chromium
```

### Celery not starting on Windows

```powershell
# Use --pool=solo flag
celery -A config worker --loglevel=info --pool=solo
```

### Firecrawl API error

- Check `.env` file has correct `FIRECRAWL_API_KEY`
- Verify API key is valid at https://firecrawl.dev

### Task not executing

- Make sure Celery worker is running
- Check Celery logs for errors
- Verify Redis is running (required for Celery broker)

---

## Documentation

See `API_DOCUMENTATION.md` for complete API reference with examples.
