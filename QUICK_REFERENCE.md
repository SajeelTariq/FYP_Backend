# 🚀 QUICK REFERENCE CARD

## Start Everything (3 Commands)

```powershell
# Terminal 1: Django
python manage.py runserver

# Terminal 2: Celery
celery -A config worker --loglevel=info --pool=solo

# Terminal 3: Redis (if not running)
docker run -d -p 6379:6379 redis
```

---

## Test Your Scripts (Copy & Paste)

```python
import requests
import time

BASE = "http://localhost:8000/api/monitoring"

# 1. Login (use your superuser credentials)
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
print(f"✅ Competitor ID: {comp_id}")

# 3. Run full pipeline (Links_extractor + Scrape_HTML + json_of_html)
r = requests.post(
    f"{BASE}/competitors/{comp_id}/run_full_pipeline/",
    headers=headers
)
task_id = r.json()['task_id']
print(f"🚀 Task started: {task_id}")
print("⏳ Check Celery terminal for progress...")

# 4. Wait and retrieve (adjust time based on website size)
time.sleep(60)

links = requests.get(f"{BASE}/extracted-links/?competitor={comp_id}", headers=headers)
html = requests.get(f"{BASE}/html-content/?competitor={comp_id}", headers=headers)
metadata = requests.get(f"{BASE}/metadata/?competitor={comp_id}", headers=headers)

print(f"\n📊 RESULTS:")
print(f"  Links extracted: {len(links.json())}")
print(f"  HTML pages: {len(html.json())}")
print(f"  Metadata entries: {len(metadata.json())}")
```

---

## API Endpoints Cheat Sheet

### Authentication

```
POST /api/monitoring/auth/register/
POST /api/monitoring/auth/login/
POST /api/monitoring/auth/logout/
```

### Competitors

```
GET  /api/monitoring/competitors/           # List
POST /api/monitoring/competitors/           # Create
GET  /api/monitoring/competitors/{id}/      # Detail
PUT  /api/monitoring/competitors/{id}/      # Update
DEL  /api/monitoring/competitors/{id}/      # Soft delete
```

### Scraping (Your Scripts!)

```
POST /api/monitoring/competitors/{id}/extract_links/      # Links_extractor.py
POST /api/monitoring/competitors/{id}/scrape_html/        # Scrape_HTML.py
POST /api/monitoring/competitors/{id}/extract_metadata/   # json_of_html.py
POST /api/monitoring/competitors/{id}/run_full_pipeline/  # All three!
```

### Data Retrieval

```
GET /api/monitoring/extracted-links/?competitor={id}    # All extracted URLs
GET /api/monitoring/html-content/?competitor={id}       # All HTML pages
GET /api/monitoring/metadata/?competitor={id}           # All metadata (for RAG)
```

---

## File Locations

### Your Original Scripts (Attachments)

```
d:\FYP\backend\src\scraper\
├── Links_extractor.py      → Now: apps/scraping/tasks.py (line 18)
├── Scrape_HTML.py         → Now: apps/scraping/tasks.py (line 120)
└── utils\
    └── json_of_html.py    → Now: apps/scraping/tasks.py (line 245)
```

### New Files Created

```
d:\FYP_Backend\
├── .env                      # Your Firecrawl API key
├── QUICKSTART.md            # 5-min setup
├── SCRAPING_INTEGRATION.md  # Detailed guide
├── SCRIPT_MIGRATION.md      # Old vs New comparison
└── SUMMARY.md               # This summary
```

---

## Database Tables

```sql
-- Your data is here (not in files anymore!)
competitor              -- Name, URLs, user_id
extracted_links         -- JSON array of URLs (replaces .txt)
competitor_html         -- HTML content (replaces .html files)
competitor_metadata     -- Clean text + metadata (replaces .json)
```

View in admin: `http://localhost:8000/admin`

---

## Troubleshooting

### ❌ Task not running?

```powershell
# Check Celery is running
celery -A config worker --loglevel=info --pool=solo
```

### ❌ Firecrawl error?

```powershell
# Check .env file
cat .env | findstr FIRECRAWL
```

### ❌ Playwright error?

```powershell
# Install browsers (one-time)
python -m playwright install chromium
```

### ❌ Database error?

```powershell
# Run migrations
python manage.py makemigrations
python manage.py migrate
```

---

## What Changed?

### Before (Your Scripts)

```
Manual execution:
1. python Links_extractor.py     → D:/FYP/backend/data/initial_links_txt/
2. python Scrape_HTML.py         → D:/FYP/backend/data/raw_html/
3. python json_of_html.py        → D:/FYP/backend/data/json_of_html/
```

### After (Django + API)

```
One API call:
POST /competitors/{id}/run_full_pipeline/
→ Everything stored in PostgreSQL
→ Accessible via API for React frontend
```

---

## Next Steps

1. ✅ Test with real website (use code above)
2. ✅ View data in admin panel
3. ⏳ Add filtering logic for links
4. ⏳ Build RAG system with metadata
5. ⏳ Connect React frontend

---

## Documentation

📖 **Start here:** [QUICKSTART.md](QUICKSTART.md)  
📚 **API Reference:** [API_DOCUMENTATION.md](API_DOCUMENTATION.md)  
🔧 **Setup Guide:** [SCRAPING_INTEGRATION.md](SCRAPING_INTEGRATION.md)  
🔄 **How Scripts Changed:** [SCRIPT_MIGRATION.md](SCRIPT_MIGRATION.md)

---

## One-Liner Test

```powershell
python -c "import requests; r = requests.post('http://localhost:8000/api/monitoring/auth/login/', json={'username': 'admin', 'password': 'admin123'}); print(f'Token: {r.json()[\"token\"]}')"
```

---

**Everything is ready! Start with `python manage.py runserver` 🎉**
