# Competitor Monitoring System - Django Backend

A comprehensive Django REST API backend for monitoring competitors, extracting data from their websites, and preparing content for RAG (Retrieval-Augmented Generation) systems.

## 🎯 Overview

This backend system integrates three core scraping operations:

1. **Link Extraction** - Uses Firecrawl API to discover all subpages
2. **HTML Scraping** - Uses Playwright to capture clean HTML content
3. **Metadata Extraction** - Prepares clean text for RAG/AI systems

All data is stored in **PostgreSQL** with user-specific isolation.

## 🏗️ Tech Stack

- **Framework**: Django 4.2.7 + Django REST Framework 3.14.0
- **Database**: PostgreSQL 14+ (via psycopg2-binary)
- **Vector Database**: Milvus 2.3.4 (for RAG system)
- **Task Queue**: Celery 5.3.4 + Redis 5.0.1
- **Web Scraping**:
  - Firecrawl API (link extraction)
  - Playwright 1.55.0 (browser automation)
  - BeautifulSoup 4.13.5 (HTML parsing)
- **ML/NLP**:
  - Transformers 4.57.1
  - Sentence-Transformers 2.2.2
  - Spacy 3.7.2
- **Authentication**: Token-based (Django REST Framework)

## 📁 Project Structure

```
FYP_Backend/
├── config/                  # Django settings and configuration
│   ├── settings.py         # Main settings (DB, Celery, Milvus, API keys)
│   ├── urls.py             # Root URL routing
│   └── celery.py           # Celery configuration
├── apps/
│   ├── monitoring/         # Core competitor management
│   │   ├── models.py       # Competitor, ExtractedLinks, HTML, Metadata
│   │   ├── views.py        # API endpoints
│   │   ├── serializers.py  # REST serializers
│   │   └── urls.py         # API routes
│   ├── scraping/           # Scraping tasks (Celery)
│   │   ├── tasks.py        # 🔥 Your scripts integrated here
│   │   └── models.py       # Scraping logs
│   ├── rag/                # RAG system (future)
│   └── analytics/          # Analytics (future)
├── scripts/                # Original Python scripts (reference)
├── utils/                  # Helper functions
├── requirements.txt        # Python dependencies
├── manage.py              # Django CLI
├── .env                   # Environment variables
└── docker-compose.yml     # PostgreSQL + Redis + Milvus

📚 Documentation:
├── API_DOCUMENTATION.md       # Complete API reference
├── SCRAPING_INTEGRATION.md   # Detailed setup guide
├── SCRIPT_MIGRATION.md       # How scripts were converted
└── QUICKSTART.md            # Quick start guide
```

## ⚡ Quick Start

### 1. Install Dependencies

```powershell
# Virtual environment (already created: myenv)
myenv\Scripts\activate

# Python packages (already installed)
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and update with your settings:

```bash
copy .env.example .env
```

### 4. Database Setup

Ensure PostgreSQL is running, then:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Start Milvus

Using Docker:

```bash
docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone
```

### 7. Start Redis

```bash
# Windows with WSL or Docker
docker run -d --name redis -p 6379:6379 redis:latest
```

### 8. Run Development Server

```bash
python manage.py runserver
```

### 9. Start Celery Worker (separate terminal)

```bash
celery -A config worker -l info
```

### 10. Start Celery Beat (separate terminal)

```bash
celery -A config beat -l info
```

## API Endpoints

### Monitoring

- `GET /api/monitoring/competitors/` - List competitors
- `POST /api/monitoring/competitors/` - Add competitor
- `GET /api/monitoring/data/` - View competitor data
- `GET /api/monitoring/tasks/` - View monitoring tasks

### Scraping

- `GET /api/scraping/configs/` - List scraping configs
- `POST /api/scraping/configs/` - Create scraping config
- `POST /api/scraping/configs/{id}/trigger_scraping/` - Trigger scraping
- `GET /api/scraping/logs/` - View scraping logs

### RAG

- `POST /api/rag/query/` - Perform RAG query
- `GET /api/rag/documents/` - List vector documents
- `GET /api/rag/logs/` - View query logs

### Analytics

- `GET /api/analytics/metrics/` - View metrics
- `GET /api/analytics/trends/` - View trends
- `GET /api/analytics/metrics/summary/` - Get metrics summary

## Admin Panel

Access at `http://localhost:8000/admin/`

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
flake8
```

## 🔥 Your Scripts - Now Integrated!

Your three scraping scripts are now fully integrated into Django:

| Original Script      | New Celery Task                 | Database Table        | API Endpoint                          |
| -------------------- | ------------------------------- | --------------------- | ------------------------------------- |
| `Links_extractor.py` | `extract_competitor_links()`    | `extracted_links`     | `/competitors/{id}/extract_links/`    |
| `Scrape_HTML.py`     | `scrape_competitor_html()`      | `competitor_html`     | `/competitors/{id}/scrape_html/`      |
| `json_of_html.py`    | `extract_competitor_metadata()` | `competitor_metadata` | `/competitors/{id}/extract_metadata/` |

### Quick Test

```python
import requests

BASE = "http://localhost:8000/api/monitoring"
token = "your_token_here"  # Get from login
headers = {"Authorization": f"Token {token}"}

# Add competitor
r = requests.post(f"{BASE}/competitors/", headers=headers, json={
    "name": "Honda Pakistan",
    "website_base_url": "https://honda.com.pk"
})
comp_id = r.json()['competitor']['id']

# Run full scraping pipeline (all 3 scripts!)
requests.post(f"{BASE}/competitors/{comp_id}/run_full_pipeline/", headers=headers)
```

**See [QUICKSTART.md](QUICKSTART.md) for complete guide!**

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference
- **[SCRAPING_INTEGRATION.md](SCRAPING_INTEGRATION.md)** - Detailed integration guide
- **[SCRIPT_MIGRATION.md](SCRIPT_MIGRATION.md)** - How your scripts were converted

## 🚀 Next Steps

- [x] ✅ Scripts integrated into Django
- [x] ✅ User authentication system
- [x] ✅ Competitor management
- [x] ✅ Async scraping tasks
- [ ] ⏳ Add link filtering logic
- [ ] ⏳ Build RAG system
- [ ] ⏳ Connect React frontend

## 📝 Notes

- ✅ All data stored in PostgreSQL (no more file management!)
- ✅ User-specific data isolation
- ✅ Celery handles async tasks
- ✅ Firecrawl API key configured in `.env`
- ✅ Playwright browsers ready (`chromium` installed)

## 📧 Support

- **Quick Issues**: See `SCRAPING_INTEGRATION.md` troubleshooting
- **API Help**: See `API_DOCUMENTATION.md`
- **Examples**: See `QUICKSTART.md`

---

**Ready to start?** Run `python manage.py runserver` and check [QUICKSTART.md](QUICKSTART.md)! 🎉
