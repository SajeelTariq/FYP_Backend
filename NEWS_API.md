# News API Endpoints

Base URL: `http://127.0.0.1:8000/api/dashboard`

---

## Authentication

Pehle token hasil karo:

```bash
curl -X POST http://127.0.0.1:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

Response:
```json
{
  "token": "abc123yourtokenhere"
}
```

Baaki tamam requests mein yeh header add karo:
```
Authorization: Token abc123yourtokenhere
```

---

## 1. News Feed (All Competitors)

Sab competitors ki news ek jagah, latest upar.

```bash
curl -X GET http://127.0.0.1:8000/api/dashboard/news/feed/ \
  -H "Authorization: Token abc123yourtokenhere"
```

### Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `days`    | 6       | Kitne din puraani news dikhani hai |
| `page`    | 1       | Pagination page number |

### Days customize karo

```bash
curl -X GET "http://127.0.0.1:8000/api/dashboard/news/feed/?days=3" \
  -H "Authorization: Token abc123yourtokenhere"
```

### Pagination

```bash
curl -X GET "http://127.0.0.1:8000/api/dashboard/news/feed/?page=2" \
  -H "Authorization: Token abc123yourtokenhere"
```

### Response

```json
{
  "days": 6,
  "total": 14,
  "page": 1,
  "page_size": 20,
  "articles": [
    {
      "title": "Honda Pakistan Recalls Thousands of Cars Across 3 Models",
      "source": "ProPakistani",
      "url": "https://propakistani.pk/...",
      "published_at": "2026-05-15T10:00:00Z",
      "fetched_at": "2026-05-15T12:00:00Z",
      "competitor_name": "Honda Pakistan"
    },
    {
      "title": "Suzuki Alto Gets Price Hike in Pakistan",
      "source": "Pakwheels",
      "url": "https://pakwheels.com/...",
      "published_at": "2026-05-14T08:00:00Z",
      "fetched_at": "2026-05-15T12:00:00Z",
      "competitor_name": "Suzuki Pakistan"
    }
  ]
}
```

---

## 2. News Correlation (Per Competitor)

Ek competitor ki news ko website changes ke saath correlate karo.

```bash
curl -X GET http://127.0.0.1:8000/api/dashboard/news/7/correlation/ \
  -H "Authorization: Token abc123yourtokenhere"
```

### Days customize karo (default 60)

```bash
curl -X GET "http://127.0.0.1:8000/api/dashboard/news/7/correlation/?days=30" \
  -H "Authorization: Token abc123yourtokenhere"
```

### Response

```json
{
  "available": true,
  "news_available": false,
  "competitor_id": 7,
  "stock_symbol": null,
  "timeline": [
    {
      "date": "2026-05-14",
      "web_changes": [
        {
          "change_type": "modified",
          "is_significant": true,
          "summary": "Homepage content updated..."
        }
      ],
      "news_articles": [],
      "correlated": false
    }
  ]
}
```

---

## How News is Fetched

| Event | What happens |
|-------|-------------|
| Competitor added | Last **6 days** ki news immediately fetch hoti hai (one-time backfill) |
| Every **2 hours** | Sirf last 2 hours ki nai news fetch hoti hai (Celery Beat) |
| Dashboard hit | Sirf DB se read hota hai — koi external call nahi |

## Notes

- `/feed/` — sab competitors ki news ek saath, `published_at` descending (latest upar)
- `competitor_name` har article mein hota hai — frontend widget mein dikhao
- `/correlation/` — DB changes + FMP financial news overlay (FMP paid plan pe depend karta hai)
- Agar `articles: []` aaye toh Celery worker chal raha ho aur competitor ka `website_base_url` set ho
