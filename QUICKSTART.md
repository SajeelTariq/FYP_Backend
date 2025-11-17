# Quick Start - Scraping Integration

## 🚀 What Changed?

Your 3 Python scripts are now **fully integrated** into Django:

| Your Script          | New Celery Task                 | Database Table        | API Endpoint                               |
| -------------------- | ------------------------------- | --------------------- | ------------------------------------------ |
| `Links_extractor.py` | `extract_competitor_links()`    | `extracted_links`     | `POST /competitors/{id}/extract_links/`    |
| `Scrape_HTML.py`     | `scrape_competitor_html()`      | `competitor_html`     | `POST /competitors/{id}/scrape_html/`      |
| `json_of_html.py`    | `extract_competitor_metadata()` | `competitor_metadata` | `POST /competitors/{id}/extract_metadata/` |

**No more file management!** All data is stored in PostgreSQL.

---

## ⚡ Quick Setup (5 Steps)

### 1. Install Playwright browsers

```powershell
python -m playwright install chromium
```

### 2. Run migrations

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 3. Start Redis (Docker)

```powershell
docker run -d -p 6379:6379 redis
```

### 4. Start Celery worker (new terminal)

```powershell
celery -A config worker --loglevel=info --pool=solo
```

### 5. Start Django server

```powershell
python manage.py runserver
```

---

## 🎯 Test It Now!

### Using Python:

```python
import requests

BASE = "http://localhost:8000/api/monitoring"

# 1. Login (or register first)
r = requests.post(f"{BASE}/auth/login/", json={
    "username": "admin",
    "password": "admin123"
})
token = r.json()['token']
headers = {"Authorization": f"Token {token}"}

# 2. Add competitor
r = requests.post(f"{BASE}/competitors/", headers=headers, json={
    "name": "Honda Pakistan",
    "website_base_url": "https://honda.com.pk"
})
comp_id = r.json()['competitor']['id']

# 3. Run scraping (one endpoint does everything!)
r = requests.post(
    f"{BASE}/competitors/{comp_id}/run_full_pipeline/",
    headers=headers
)
print(r.json())
# Output: {'status': 'Task started', 'task_id': '...'}

# 4. Wait ~60 seconds, then retrieve data
import time
time.sleep(60)

# Get results from database
links = requests.get(f"{BASE}/extracted-links/?competitor={comp_id}", headers=headers)
html = requests.get(f"{BASE}/html-content/?competitor={comp_id}", headers=headers)
metadata = requests.get(f"{BASE}/metadata/?competitor={comp_id}", headers=headers)

print(f"Links extracted: {len(links.json())}")
print(f"HTML pages: {len(html.json())}")
print(f"Metadata entries: {len(metadata.json())}")
```

---

## 🔍 What Happens Behind the Scenes?

When you call `run_full_pipeline/`:

1. **Extract Links** (Firecrawl API)

   ```
   [INFO] 🌐 Calling Firecrawl API for honda.com.pk
   [INFO] ✅ Extracted 150 links
   [INFO] 💾 Stored in extracted_links table
   ```

2. **Scrape HTML** (Playwright)

   ```
   [INFO] 🌐 Scraping: https://honda.com.pk/about
   [INFO] 🧹 Removing CSS and inline styles
   [INFO] ✅ Saved HTML to competitor_html table
   ```

3. **Extract Metadata** (BeautifulSoup)
   ```
   [INFO] 📄 Processing HTML for honda.com.pk/about
   [INFO] 🧹 Cleaning text, removing duplicates
   [INFO] ✅ Stored metadata for RAG system
   ```

---

## 📊 View in Admin Panel

1. Go to `http://localhost:8000/admin`
2. Login with superuser credentials
3. See all scraped data:
   - **Competitors** → your added competitors
   - **Extracted Links** → all URLs found
   - **Competitor HTML** → scraped HTML content
   - **Competitor Metadata** → clean text for RAG

---

## 🎨 Frontend Integration (React)

```javascript
// Add competitor
const response = await fetch(
  "http://localhost:8000/api/monitoring/competitors/",
  {
    method: "POST",
    headers: {
      Authorization: `Token ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: "Honda Pakistan",
      website_base_url: "https://honda.com.pk",
    }),
  }
);
const { competitor } = await response.json();

// Trigger scraping
await fetch(
  `http://localhost:8000/api/monitoring/competitors/${competitor.id}/run_full_pipeline/`,
  {
    method: "POST",
    headers: {
      Authorization: `Token ${token}`,
      "Content-Type": "application/json",
    },
  }
);

// Show "Scraping in progress..." to user
// Poll for results after ~60 seconds
```

---

## 🔧 Environment Variables

Your `.env` file is configured with:

```env
FIRECRAWL_API_KEY=fc-c142a5e31e0a4f79ac59182c6fc2e22a
DATABASE_NAME=competitor_monitoring
DATABASE_USER=postgres
DATABASE_PASSWORD=yourpassword
```

**Update** `DATABASE_PASSWORD` to match your PostgreSQL setup.

---

## 📖 Full Documentation

- **API Reference**: `API_DOCUMENTATION.md`
- **Detailed Setup**: `SCRAPING_INTEGRATION.md`
- **Original README**: `README.md`

---

## ✨ What's Next?

- ✅ Your scripts are integrated
- ✅ Data stored in database
- ✅ API endpoints ready
- ⏳ Add link filtering logic
- ⏳ Build RAG system using metadata
- ⏳ Connect React frontend
- ⏳ Add scheduled daily scraping

**You're ready to test!** 🎉
