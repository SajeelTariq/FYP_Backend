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

## 1. News Feed

Competitor ki last 6 days ki news DB se fetch karo.

```bash
curl -X GET http://127.0.0.1:8000/api/dashboard/news/7/feed/ \
  -H "Authorization: Token abc123yourtokenhere"
```

### Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `days`    | 6       | Kitne din puraani news dikhani hai |
| `page`    | 1       | Pagination page number |

### Days customize karo

```bash
curl -X GET "http://127.0.0.1:8000/api/dashboard/news/7/feed/?days=3" \
  -H "Authorization: Token abc123yourtokenhere"
```

### Pagination

```bash
curl -X GET "http://127.0.0.1:8000/api/dashboard/news/7/feed/?page=2" \
  -H "Authorization: Token abc123yourtokenhere"
```

### Response

```json
{
  "competitor_id": 7,
  "competitor_name": "Honda Pakistan",
  "days": 6,
  "total": 3,
  "page": 1,
  "page_size": 20,
  "articles": [
    {
      "title": "Honda Pakistan Recalls Thousands of Cars Across 3 Models",
      "source": "ProPakistani",
      "url": "https://propakistani.pk/...",
      "published_at": "2026-05-13T10:00:00Z",
      "fetched_at": "2026-05-14T15:35:00Z"
    },
    {
      "title": "Honda Pakistan Issues Airbag Recall for Three Models",
      "source": "Pakwheels",
      "url": "https://pakwheels.com/...",
      "published_at": "2026-05-12T08:00:00Z",
      "fetched_at": "2026-05-14T15:35:00Z"
    }
  ]
}
```

---

## 2. News Correlation

Competitor ki news ko website changes ke saath correlate karo.

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
      "date": "2026-05-13",
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

## Notes

- `/feed/` — DB se read karta hai, Celery har **6 ghante** mein automatically update karta hai
- `/correlation/` — DB changes + FMP financial news overlay (FMP paid plan pe depend karta hai)
- Agar `articles: []` aaye toh Celery task pehle manually run karo (news abhi DB mein nahi hai)
