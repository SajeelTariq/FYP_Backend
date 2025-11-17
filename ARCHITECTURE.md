# System Architecture & Data Flow

## 🏗️ Overall Architecture

```
┌─────────────────┐
│  React Frontend │
│   (Your Team)   │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────────────────────────────────────────────┐
│                    Django Backend                        │
│  ┌────────────────────────────────────────────────────┐ │
│  │          API Endpoints (views.py)                  │ │
│  │  • Auth (register/login/logout)                    │ │
│  │  • Competitors (CRUD + scraping actions)           │ │
│  │  • Data retrieval (links/html/metadata)            │ │
│  └────────┬───────────────────────────────────────────┘ │
│           │                                              │
│           ▼                                              │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Database Models (models.py)                │ │
│  │  • Competitor, ExtractedLinks, FilteredLinks      │ │
│  │  • CompetitorHTML, CompetitorMetadata             │ │
│  └────────┬───────────────────────────────────────────┘ │
└───────────┼──────────────────────────────────────────────┘
            │
            ▼
  ┌──────────────────┐         ┌──────────────────┐
  │   PostgreSQL     │         │   Redis Broker   │
  │  (Data Storage)  │         │  (Task Queue)    │
  └──────────────────┘         └────────┬─────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │    Celery Workers        │
                          │  ┌────────────────────┐ │
                          │  │ Your Scripts Here! │ │
                          │  ├────────────────────┤ │
                          │  │ extract_links()    │ │
                          │  │ scrape_html()      │ │
                          │  │ extract_metadata() │ │
                          │  └────────────────────┘ │
                          └──────────┬───────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  External Services   │
                          │  • Firecrawl API     │
                          │  • Playwright        │
                          └──────────────────────┘
```

---

## 📊 Data Flow: Adding & Scraping a Competitor

### Step 1: User Adds Competitor

```
Frontend Request:
POST /api/monitoring/competitors/
{
  "name": "Honda Pakistan",
  "website_base_url": "https://honda.com.pk"
}
         │
         ▼
Django View (views.py):
CompetitorViewSet.create()
  • Check if competitor exists (duplicate detection)
  • Update if exists, create if new
         │
         ▼
PostgreSQL:
INSERT INTO competitor
(user_id, name, website_base_url, ...)
         │
         ▼
Response:
{
  "competitor": {
    "id": 1,
    "name": "Honda Pakistan",
    ...
  },
  "created": true
}
```

### Step 2: User Triggers Scraping

```
Frontend Request:
POST /api/monitoring/competitors/1/run_full_pipeline/
         │
         ▼
Django View (views.py):
CompetitorViewSet.run_full_pipeline()
  • Get competitor object
  • Call Celery task asynchronously
         │
         ▼
Celery Task Queue (Redis):
Task: run_full_scraping_pipeline(competitor_id=1)
  Status: PENDING
         │
         ▼
Response to Frontend:
{
  "status": "Task started",
  "task_id": "abc123",
  "competitor": "Honda Pakistan"
}
```

### Step 3: Celery Worker Executes (Background)

#### Sub-step 3a: Extract Links

```
Celery Worker:
run_full_scraping_pipeline(1)
  └─> extract_competitor_links(1)
      │
      ▼
Your Original Logic (Links_extractor.py):
  1. Get competitor: "honda.com.pk"
  2. Validate URL format
  3. Check website exists (HEAD request)
  4. Call Firecrawl API:
     POST https://api.firecrawl.dev/v2/map
     {
       "url": "https://honda.com.pk",
       "limit": 5000
     }
      │
      ▼
Firecrawl Response:
{
  "links": [
    {"url": "https://honda.com.pk/about"},
    {"url": "https://honda.com.pk/products"},
    {"url": "https://honda.com.pk/contact"},
    ...150 more URLs
  ]
}
      │
      ▼
PostgreSQL:
INSERT/UPDATE extracted_links
(competitor_id=1, links=['...', '...'])
      │
      ▼
Log: ✅ Extracted 150 links for Honda Pakistan
```

#### Sub-step 3b: Scrape HTML

```
Celery Worker:
run_full_scraping_pipeline(1)
  └─> scrape_competitor_html(1, use_filtered=False)
      │
      ▼
Get Links from DB:
SELECT links FROM extracted_links WHERE competitor_id=1
  → ['https://honda.com.pk/about', ...]
      │
      ▼
Your Original Logic (Scrape_HTML.py):
  FOR EACH url IN links:
    1. Launch Playwright (Chromium headless)
    2. Navigate to URL
    3. Wait for page load (domcontentloaded)
    4. Execute JavaScript:
       - Remove <style>, <link rel="stylesheet">
       - Remove inline style attributes
    5. Get cleaned HTML
    6. Beautify with BeautifulSoup
       │
       ▼
    PostgreSQL:
    INSERT/UPDATE competitor_html
    (competitor_id=1, url='...', html_content='...')
       │
       ▼
    Log: ✅ Saved HTML for: https://honda.com.pk/about
      │
      ▼
Log: ✅ Scraped 150/150 pages for Honda Pakistan
```

#### Sub-step 3c: Extract Metadata

```
Celery Worker:
run_full_scraping_pipeline(1)
  └─> extract_competitor_metadata(1)
      │
      ▼
Get HTML from DB:
SELECT * FROM competitor_html WHERE competitor_id=1
      │
      ▼
Your Original Logic (json_of_html.py):
  FOR EACH html_entry IN html_objects:
    1. Parse with BeautifulSoup
    2. Remove non-visible tags (script, style, svg, ...)
    3. Extract text content
    4. Clean whitespace, remove duplicates (MD5 hash)
    5. Extract title from <title> tag
    6. Create metadata JSON:
       {
         "url": "...",
         "title": "...",
         "content": "cleaned text...",
         "content_length": 5000,
         "line_count": 250
       }
       │
       ▼
    PostgreSQL:
    INSERT/UPDATE competitor_metadata
    (competitor_id=1, url='...', metadata={...})
       │
       ▼
    Log: ✅ Processed metadata for: https://honda.com.pk/about
      │
      ▼
Log: ✅ Processed 150/150 pages for Honda Pakistan
```

### Step 4: Frontend Retrieves Data

```
Frontend Request:
GET /api/monitoring/extracted-links/?competitor=1
         │
         ▼
Django View:
ExtractedLinksViewSet.list()
  • Filter by competitor_id=1
  • Filter by current user
         │
         ▼
PostgreSQL:
SELECT * FROM extracted_links
WHERE competitor_id=1 AND competitor.user_id=current_user
         │
         ▼
Response:
[
  {
    "id": 1,
    "competitor": 1,
    "links": ["https://honda.com.pk/about", ...],
    "extracted_at": "2025-11-16T10:00:00Z"
  }
]

Similar for:
GET /api/monitoring/html-content/?competitor=1
GET /api/monitoring/metadata/?competitor=1
```

---

## 🔄 File-Based vs Database-Based Comparison

### Your Original Approach (File-Based)

```
1. Links_extractor.py
   INPUT: User types "honda.com.pk"
   OUTPUT: D:\FYP\backend\data\initial_links_txt\honda.txt

   honda.txt:
   https://honda.com.pk/about
   https://honda.com.pk/products
   https://honda.com.pk/contact
   ...

2. Scrape_HTML.py
   INPUT: Read D:\FYP\backend\data\initial_links_txt\honda.txt
   OUTPUT: D:\FYP\backend\data\raw_html\honda\

   raw_html\honda\:
   ├── https__honda-com-pk_about.html (5 MB)
   ├── https__honda-com-pk_products.html (3 MB)
   └── https__honda-com-pk_contact.html (2 MB)

3. json_of_html.py
   INPUT: Read D:\FYP\backend\data\raw_html\honda\*.html
   OUTPUT: D:\FYP\backend\data\json_of_html\honda\

   json_of_html\honda\:
   ├── https__honda-com-pk_about.json
   ├── https__honda-com-pk_products.json
   └── https__honda-com-pk_contact.json

Problems:
❌ Manual execution for each step
❌ Hard to manage file paths
❌ No user isolation (all data mixed)
❌ Frontend can't access files directly
❌ Difficult to query/filter
❌ No error recovery
```

### New Approach (Database-Based)

```
1. extract_competitor_links(competitor_id)
   INPUT: competitor_id=1 (from DB)
   OUTPUT: PostgreSQL table 'extracted_links'

   extracted_links:
   | id | competitor_id | links (JSON)                          |
   |----|---------------|---------------------------------------|
   | 1  | 1             | ["https://honda.com.pk/about", ...]  |

2. scrape_competitor_html(competitor_id)
   INPUT: Links from 'extracted_links' table
   OUTPUT: PostgreSQL table 'competitor_html'

   competitor_html:
   | id | competitor_id | url                          | html_content     |
   |----|---------------|------------------------------|------------------|
   | 1  | 1             | https://honda.com.pk/about   | <!DOCTYPE html>  |
   | 2  | 1             | https://honda.com.pk/products| <!DOCTYPE html>  |

3. extract_competitor_metadata(competitor_id)
   INPUT: HTML from 'competitor_html' table
   OUTPUT: PostgreSQL table 'competitor_metadata'

   competitor_metadata:
   | id | competitor_id | url                          | metadata (JSON)  |
   |----|---------------|------------------------------|------------------|
   | 1  | 1             | https://honda.com.pk/about   | {"title": ".."}  |
   | 2  | 1             | https://honda.com.pk/products| {"title": ".."}  |

Benefits:
✅ One API call triggers all steps
✅ No file path management
✅ User isolation (user_id in competitor table)
✅ Frontend accesses via API
✅ SQL queries for filtering
✅ Automatic retry on failure
```

---

## 🎯 User Data Isolation

```
User 1 (john@example.com)
├── Competitor: Honda Pakistan (id=1)
│   ├── extracted_links: 150 URLs
│   ├── competitor_html: 150 pages
│   └── competitor_metadata: 150 entries
└── Competitor: Suzuki Pakistan (id=2)
    ├── extracted_links: 200 URLs
    ├── competitor_html: 200 pages
    └── competitor_metadata: 200 entries

User 2 (jane@example.com)
├── Competitor: Kia Motors (id=3)
│   ├── extracted_links: 180 URLs
│   ├── competitor_html: 180 pages
│   └── competitor_metadata: 180 entries
└── Competitor: Tesla (id=4)
    ├── extracted_links: 250 URLs
    ├── competitor_html: 250 pages
    └── competitor_metadata: 250 entries

Django automatically filters:
- User 1 can only see competitors 1 & 2
- User 2 can only see competitors 3 & 4
- API queries are user-specific
```

---

## 🔐 Authentication Flow

```
1. Registration:
   POST /api/monitoring/auth/register/
   {"username": "john", "password": "pass123"}
   │
   ▼
   Django creates User object
   Django creates Token object
   │
   ▼
   Returns: {"user": {...}, "token": "abc123..."}

2. Login:
   POST /api/monitoring/auth/login/
   {"username": "john", "password": "pass123"}
   │
   ▼
   Django authenticates user
   Django retrieves/creates Token
   │
   ▼
   Returns: {"user": {...}, "token": "abc123..."}

3. Authenticated Request:
   POST /api/monitoring/competitors/
   Headers: {"Authorization": "Token abc123..."}
   │
   ▼
   Django validates token
   Django sets request.user
   │
   ▼
   View accesses request.user
   Creates competitor with user=request.user
```

---

## 📱 Frontend Integration Example

```javascript
// React component
const CompetitorScraping = () => {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [competitors, setCompetitors] = useState([]);
  const [scraping, setScraping] = useState(false);

  // Add competitor
  const addCompetitor = async (name, website) => {
    const response = await fetch(
      "http://localhost:8000/api/monitoring/competitors/",
      {
        method: "POST",
        headers: {
          Authorization: `Token ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, website_base_url: website }),
      }
    );
    const data = await response.json();
    return data.competitor.id;
  };

  // Trigger scraping
  const startScraping = async (competitorId) => {
    setScraping(true);
    const response = await fetch(
      `http://localhost:8000/api/monitoring/competitors/${competitorId}/run_full_pipeline/`,
      {
        method: "POST",
        headers: { Authorization: `Token ${token}` },
      }
    );
    const data = await response.json();

    // Show "Scraping in progress..." to user
    // Poll for results or use WebSocket for real-time updates
    setTimeout(() => fetchResults(competitorId), 60000);
  };

  // Fetch results
  const fetchResults = async (competitorId) => {
    const links = await fetch(
      `http://localhost:8000/api/monitoring/extracted-links/?competitor=${competitorId}`,
      { headers: { Authorization: `Token ${token}` } }
    );
    const html = await fetch(
      `http://localhost:8000/api/monitoring/html-content/?competitor=${competitorId}`,
      { headers: { Authorization: `Token ${token}` } }
    );
    const metadata = await fetch(
      `http://localhost:8000/api/monitoring/metadata/?competitor=${competitorId}`,
      { headers: { Authorization: `Token ${token}` } }
    );

    setScraping(false);
    // Display results to user
  };

  return (
    <div>
      <button
        onClick={() =>
          addCompetitor("Honda", "honda.com.pk").then((id) => startScraping(id))
        }
      >
        Add & Scrape Competitor
      </button>
      {scraping && <p>Scraping in progress...</p>}
    </div>
  );
};
```

---

## 🚀 Scaling Considerations

```
Current Setup (Single Server):
┌──────────────────────────────────────┐
│  Django + Celery on one machine      │
│  • Good for development/testing      │
│  • Handles ~10 concurrent scrapings  │
└──────────────────────────────────────┘

Production Setup (Distributed):
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Django     │    │  Celery     │    │  Celery     │
│  Server 1   │───▶│  Worker 1   │    │  Worker 2   │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                   │
       └──────────────────┼───────────────────┘
                          ▼
                 ┌─────────────────┐
                 │   PostgreSQL    │
                 │   (Managed DB)  │
                 └─────────────────┘
                          ▲
                          │
                 ┌─────────────────┐
                 │   Redis         │
                 │   (Task Queue)  │
                 └─────────────────┘

Benefits:
✅ Multiple workers scrape in parallel
✅ Django server handles API requests only
✅ Can scale workers independently
✅ Managed database for reliability
```

---

This architecture ensures your original script logic is preserved while gaining all the benefits of a modern web application!
