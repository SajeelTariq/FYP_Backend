# ✅ Setup & Testing Checklist

Use this checklist to ensure everything is configured and working correctly.

---

## Pre-requisites ✓

- [x] Python 3.10+ installed
- [x] Virtual environment created (`myenv`)
- [x] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Playwright browsers installed

```powershell
python -m playwright install chromium
```

---

## One-Time Setup ✓

### 1. Environment Variables

- [ ] `.env` file exists in project root
- [ ] `FIRECRAWL_API_KEY` is set (already done: `fc-c142a5e31e0a4f79ac59182c6fc2e22a`)
- [ ] Database credentials configured (update if needed)

```powershell
# Check .env file
cat .env
```

### 2. Database Setup

- [ ] PostgreSQL is running (Docker or local)
- [ ] Database created (or will be created on first run)
- [ ] Migrations run

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 3. Superuser Account

- [ ] Superuser created for admin access

```powershell
python manage.py createsuperuser
# Enter: username, email, password
```

### 4. Redis for Celery

- [ ] Redis is running (required for Celery)

```powershell
# Option 1: Docker
docker run -d --name redis -p 6379:6379 redis

# Option 2: Check if already running
docker ps | findstr redis
```

---

## Starting Services ✓

### Terminal 1: Django Server

- [ ] Activated virtual environment
- [ ] Django server running on port 8000

```powershell
cd d:\FYP_Backend
myenv\Scripts\activate
python manage.py runserver
```

**Expected output:**

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Terminal 2: Celery Worker

- [ ] Activated virtual environment
- [ ] Celery worker running with `--pool=solo`

```powershell
cd d:\FYP_Backend
myenv\Scripts\activate
celery -A config worker --loglevel=info --pool=solo
```

**Expected output:**

```
 -------------- celery@YOURPC v5.3.4
---- **** -----
--- * ***  * -- Windows-10-...
-- * - **** ---
- ** ---------- [config]
- ** ---------- .> app:         config:0x...
- *** --- * --- .> transport:   redis://localhost:6379//
-- ******* ---- .> results:     disabled://
--- ***** ----- .> concurrency: 1 (solo)

[tasks]
  . apps.scraping.tasks.extract_competitor_links
  . apps.scraping.tasks.scrape_competitor_html
  . apps.scraping.tasks.extract_competitor_metadata
  . apps.scraping.tasks.run_full_scraping_pipeline
```

---

## Basic Testing ✓

### 1. Django Server Health Check

- [ ] Server responds at root URL

```powershell
# In browser or new terminal:
curl http://localhost:8000/
```

### 2. Admin Panel Access

- [ ] Can access admin panel
- [ ] Can login with superuser

```
Browser: http://localhost:8000/admin
Login with your superuser credentials
```

**Expected:** Should see Django admin interface

### 3. API Endpoints Available

- [ ] API root responds

```powershell
curl http://localhost:8000/api/monitoring/
```

### 4. Redis Connection

- [ ] Celery can connect to Redis

**Check Celery terminal:** Should say "Connected" with no errors

---

## Authentication Testing ✓

### 1. Register New User

- [ ] Can register via API

```powershell
curl -X POST http://localhost:8000/api/monitoring/auth/register/ `
  -H "Content-Type: application/json" `
  -d '{\"username\": \"testuser\", \"email\": \"test@test.com\", \"password\": \"testpass123\", \"password_confirm\": \"testpass123\"}'
```

**Expected:** Returns user object and token

### 2. Login

- [ ] Can login and get token

```powershell
curl -X POST http://localhost:8000/api/monitoring/auth/login/ `
  -H "Content-Type: application/json" `
  -d '{\"username\": \"testuser\", \"password\": \"testpass123\"}'
```

**Expected:** Returns token like `{"user": {...}, "token": "abc123..."}`

**Save your token** for next steps!

---

## Core Functionality Testing ✓

### 1. Add Competitor

- [ ] Can create competitor via API

**PowerShell:**

```powershell
$token = "YOUR_TOKEN_HERE"
$headers = @{"Authorization" = "Token $token"; "Content-Type" = "application/json"}
$body = '{"name": "Test Company", "website_base_url": "https://example.com"}'

Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/competitors/" `
  -Method POST -Headers $headers -Body $body
```

**Expected:** Returns competitor object with ID

### 2. List Competitors

- [ ] Can retrieve competitors

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/competitors/" `
  -Method GET -Headers $headers
```

**Expected:** Array with your test competitor

---

## Scraping Testing (Your Scripts!) ✓

### 1. Extract Links

- [ ] Can trigger link extraction
- [ ] Celery worker processes task
- [ ] Links stored in database

```powershell
$competitorId = 1  # Use ID from previous step
Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/competitors/$competitorId/extract_links/" `
  -Method POST -Headers $headers
```

**Expected:**

- Response: `{"status": "Task started", "task_id": "...", ...}`
- **Check Celery terminal:** Should show:
  ```
  [INFO] 🌐 Calling Firecrawl API for example.com
  [INFO] ✅ Extracted X links for Test Company
  ```

### 2. Retrieve Extracted Links

- [ ] Can get extracted links from database

```powershell
Start-Sleep -Seconds 10  # Wait for task to complete
Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/extracted-links/?competitor=$competitorId" `
  -Method GET -Headers $headers
```

**Expected:** Array with links JSON field

### 3. Scrape HTML

- [ ] Can trigger HTML scraping
- [ ] Playwright works correctly
- [ ] HTML stored in database

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/competitors/$competitorId/scrape_html/" `
  -Method POST -Headers $headers -Body '{"use_filtered_links": false}'
```

**Expected:**

- Response: `{"status": "Task started", ...}`
- **Check Celery terminal:**
  ```
  [INFO] 🌐 Scraping: https://example.com/about
  [INFO] ✅ Saved HTML for: https://example.com/about
  ```

### 4. Retrieve HTML Content

- [ ] Can get scraped HTML from database

```powershell
Start-Sleep -Seconds 30
Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/html-content/?competitor=$competitorId" `
  -Method GET -Headers $headers
```

**Expected:** Array with HTML content entries

### 5. Extract Metadata

- [ ] Can trigger metadata extraction
- [ ] Metadata processed and stored

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/competitors/$competitorId/extract_metadata/" `
  -Method POST -Headers $headers
```

**Expected:**

- Response: `{"status": "Task started", ...}`
- **Check Celery terminal:**
  ```
  [INFO] 📄 Processing HTML for example.com/about
  [INFO] ✅ Processed metadata for: example.com/about
  ```

### 6. Retrieve Metadata

- [ ] Can get metadata from database

```powershell
Start-Sleep -Seconds 10
Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/metadata/?competitor=$competitorId" `
  -Method GET -Headers $headers
```

**Expected:** Array with metadata JSON objects

---

## Full Pipeline Testing ✓

### Run Complete Pipeline

- [ ] Can run all three scripts in sequence
- [ ] All data stored correctly

```powershell
$competitorId = 2  # Create new competitor for clean test
$body = '{"name": "Honda Pakistan", "website_base_url": "https://honda.com.pk"}'
$comp = Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/competitors/" `
  -Method POST -Headers $headers -Body $body

$competitorId = $comp.competitor.id

# Run full pipeline
Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/competitors/$competitorId/run_full_pipeline/" `
  -Method POST -Headers $headers
```

**Wait 60-120 seconds** (depending on website size)

**Check Celery terminal for complete flow:**

```
[INFO] 🚀 Starting full scraping pipeline for Honda Pakistan
[INFO] Step 1: Extracting links...
[INFO] ✅ Extracted 150 links for Honda Pakistan
[INFO] Step 2: Scraping HTML...
[INFO] 🌐 Scraping: https://honda.com.pk/about
[INFO] ✅ Saved HTML for: https://honda.com.pk/about
[INFO] ... (more pages)
[INFO] Step 3: Extracting metadata...
[INFO] ✅ Processed metadata for: https://honda.com.pk/about
[INFO] ... (more pages)
[INFO] ✅ Completed full pipeline for Honda Pakistan
```

**Retrieve all data:**

```powershell
$links = Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/extracted-links/?competitor=$competitorId" -Method GET -Headers $headers
$html = Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/html-content/?competitor=$competitorId" -Method GET -Headers $headers
$metadata = Invoke-RestMethod -Uri "http://localhost:8000/api/monitoring/metadata/?competitor=$competitorId" -Method GET -Headers $headers

Write-Host "Links extracted: $($links.Count)"
Write-Host "HTML pages: $($html.Count)"
Write-Host "Metadata entries: $($metadata.Count)"
```

---

## Admin Panel Verification ✓

### Check Data in Admin

- [ ] Navigate to `http://localhost:8000/admin`
- [ ] Login with superuser
- [ ] Verify data exists:
  - [ ] **Competitors** table has entries
  - [ ] **Extracted Links** table has data
  - [ ] **Competitor HTML** table has HTML content
  - [ ] **Competitor Metadata** table has metadata
- [ ] Check user isolation (only see your own data)

---

## Common Issues & Solutions ✓

### ❌ Issue: "No module named 'playwright'"

**Solution:**

```powershell
pip install playwright
python -m playwright install chromium
```

### ❌ Issue: "Connection refused" (Redis)

**Solution:**

```powershell
docker run -d --name redis -p 6379:6379 redis
```

### ❌ Issue: "Task not executing"

**Solution:**

- Check Celery worker is running
- Check Redis is running
- Check Celery terminal for errors

### ❌ Issue: "Firecrawl API error"

**Solution:**

- Verify `.env` has correct `FIRECRAWL_API_KEY`
- Check API key at https://firecrawl.dev

### ❌ Issue: "Table does not exist"

**Solution:**

```powershell
python manage.py makemigrations
python manage.py migrate
```

### ❌ Issue: "Token authentication failed"

**Solution:**

- Make sure to include header: `Authorization: Token YOUR_TOKEN`
- Get fresh token by logging in again

---

## Python Test Script (All-in-One) ✓

Save this as `test_scraping.py` and run to test everything:

```python
import requests
import time

BASE = "http://localhost:8000/api/monitoring"

print("🔐 1. Login...")
r = requests.post(f"{BASE}/auth/login/", json={
    "username": "YOUR_USERNAME",  # Update this
    "password": "YOUR_PASSWORD"   # Update this
})
if r.status_code != 200:
    print(f"❌ Login failed: {r.text}")
    exit()
token = r.json()['token']
print(f"✅ Token: {token[:20]}...")
headers = {"Authorization": f"Token {token}"}

print("\n📝 2. Adding competitor...")
r = requests.post(f"{BASE}/competitors/", headers=headers, json={
    "name": "Test Scraping Company",
    "website_base_url": "https://example.com"
})
if r.status_code not in [200, 201]:
    print(f"❌ Failed to add competitor: {r.text}")
    exit()
comp_id = r.json()['competitor']['id']
print(f"✅ Competitor ID: {comp_id}")

print("\n🚀 3. Starting full pipeline...")
r = requests.post(f"{BASE}/competitors/{comp_id}/run_full_pipeline/", headers=headers)
if r.status_code != 202:
    print(f"❌ Failed to start pipeline: {r.text}")
    exit()
task_id = r.json()['task_id']
print(f"✅ Task ID: {task_id}")
print("⏳ Waiting 60 seconds for scraping to complete...")
time.sleep(60)

print("\n📊 4. Retrieving results...")
links = requests.get(f"{BASE}/extracted-links/?competitor={comp_id}", headers=headers)
html = requests.get(f"{BASE}/html-content/?competitor={comp_id}", headers=headers)
metadata = requests.get(f"{BASE}/metadata/?competitor={comp_id}", headers=headers)

print(f"\n✅ RESULTS:")
print(f"  Links extracted: {len(links.json())}")
print(f"  HTML pages: {len(html.json())}")
print(f"  Metadata entries: {len(metadata.json())}")

if len(links.json()) > 0:
    print("\n🎉 SUCCESS! All systems working correctly!")
else:
    print("\n⚠️  No links found. Check Celery worker logs.")
```

Run it:

```powershell
python test_scraping.py
```

---

## Final Verification ✓

- [ ] Django server running without errors
- [ ] Celery worker running and processing tasks
- [ ] Redis running and accepting connections
- [ ] Can register/login users
- [ ] Can add competitors
- [ ] Can trigger scraping (all 3 scripts)
- [ ] Data stored in PostgreSQL
- [ ] Admin panel shows data
- [ ] All Python tests pass

---

## 🎉 You're Ready!

If all checkboxes are ✅, your system is fully operational!

**Next Steps:**

1. Test with real websites (Honda, Suzuki, etc.)
2. Build link filtering logic
3. Integrate RAG system
4. Connect React frontend

---

**Need help?** Check:

- [QUICKSTART.md](QUICKSTART.md) - Quick setup
- [SCRAPING_INTEGRATION.md](SCRAPING_INTEGRATION.md) - Detailed guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- Celery worker logs for task execution details
