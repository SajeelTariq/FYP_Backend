# Reports API Documentation

Base URL: `http://127.0.0.1:8000`

All endpoints require authentication. Include the token in every request header:
```
Authorization: Token <your_token_here>
```

---

## Authentication

### Login
```bash
curl -X POST http://127.0.0.1:8000/api/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**Response:**
```json
{
  "user": {
    "id": 2,
    "username": "admin",
    "email": "admin@example.com"
  },
  "token": "7827a9bd13de7cbbf7f43b3ef0ab3f12cd3ccdf2"
}
```

---

## Reports

### 1. Generate Report

Triggers report generation in the background. Returns immediately with a `report_id`.

```bash
curl -X POST http://127.0.0.1:8000/api/reports/generate/ \
  -H "Authorization: Token <your_token_here>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q4 Competitive Analysis",
    "report_type": "executive",
    "period_start": "2026-04-10",
    "period_end": "2026-05-10",
    "competitor_ids": []
  }'
```

**Body Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Report title shown on frontend and used for search |
| `report_type` | string | Yes | `"executive"` or `"analyst"` |
| `period_start` | string | Yes | Start date in `YYYY-MM-DD` format |
| `period_end` | string | Yes | End date in `YYYY-MM-DD` format (max 30 days after `period_start`, cannot be in the future) |
| `competitor_ids` | array | Yes | List of competitor IDs. Empty array `[]` = all competitors |

**Validation Rules:**
- `period_end` must be on or after `period_start`
- Date range cannot exceed 30 days
- `period_end` cannot be in the future

**Response `202 Accepted`:**
```json
{
  "message": "Report generation started.",
  "report_id": 8,
  "status": "pending",
  "period_start": "2026-04-10",
  "period_end": "2026-05-10"
}
```

> **Note:** Celery worker must be running for report generation to proceed past `pending`.
> Start with: `python -m celery -A config worker --loglevel=info --pool=solo`

---

### 2. Check Report Status

Poll this endpoint every 3 seconds until `status` becomes `"completed"` or `"failed"`.

```bash
curl -X GET http://127.0.0.1:8000/api/reports/8/ \
  -H "Authorization: Token <your_token_here>"
```

**Response:**
```json
{
  "id": 8,
  "title": "Q4 Competitive Analysis",
  "report_type": "executive",
  "status": "completed",
  "period_start": "2026-05-01",
  "period_end": "2026-05-07",
  "content": { ... },
  "error_message": "",
  "created_at": "2026-05-07T10:00:00Z",
  "completed_at": "2026-05-07T10:00:25Z"
}
```

**Possible `status` values:**

| Status | Meaning |
|--------|---------|
| `pending` | Queued, not started yet |
| `generating` | LLM is generating the report |
| `completed` | Ready — show Download button |
| `failed` | Something went wrong — check `error_message` |

---

### 3. Download Report as PDF

Call this only when `status == "completed"`. Returns a PDF file.

```bash
curl -X GET http://127.0.0.1:8000/api/reports/8/pdf/ \
  -H "Authorization: Token <your_token_here>" \
  --output report.pdf
```

The response is a PDF file download with:
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="report_executive_2026-05-01_2026-05-07.pdf"
```

---

### 4. List Reports

Returns all reports for the logged-in user. Supports filtering by type and period.

```bash
# All reports
curl -X GET http://127.0.0.1:8000/api/reports/ \
  -H "Authorization: Token <your_token_here>"

# Filter by type
curl -X GET "http://127.0.0.1:8000/api/reports/?type=executive" \
  -H "Authorization: Token <your_token_here>"

# Filter by period (reports created in last N days)
curl -X GET "http://127.0.0.1:8000/api/reports/?period=30" \
  -H "Authorization: Token <your_token_here>"

# Filter by both type and period
curl -X GET "http://127.0.0.1:8000/api/reports/?type=analyst&period=7" \
  -H "Authorization: Token <your_token_here>"

# Search by title
curl -X GET "http://127.0.0.1:8000/api/reports/?search=Q4" \
  -H "Authorization: Token <your_token_here>"

# Combine all filters
curl -X GET "http://127.0.0.1:8000/api/reports/?type=executive&period=30&search=Q4" \
  -H "Authorization: Token <your_token_here>"
```

**Query Parameters:**

| Param | Values | Description |
|-------|--------|-------------|
| `type` | `executive`, `analyst` | Filter by report type |
| `period` | `7`, `30`, `90` | Show reports created in last N days |
| `search` | any string | Search reports by title (case-insensitive) |

**Response:**
```json
[
  {
    "id": 8,
    "title": "Q4 Competitive Analysis",
    "report_type": "executive",
    "status": "completed",
    "period_start": "2026-05-01",
    "period_end": "2026-05-07",
    "created_at": "2026-05-07T10:00:00Z",
    "completed_at": "2026-05-07T10:00:25Z"
  }
]
```

---

### 5. Preview Report (JSON)

Returns full report content as JSON — use this for in-app preview before downloading PDF.

```bash
curl -X GET http://127.0.0.1:8000/api/reports/8/ \
  -H "Authorization: Token <your_token_here>"
```

---

## Frontend Flow

```
1. User enters a report title
2. User selects report type (Executive / Analyst)
3. User picks a start date and end date (max 30-day range, end date cannot be in the future)
4. User clicks "Generate Report"

   POST /api/reports/generate/
   → Save report_id from response

4. Show loading spinner
   Poll every 3 seconds: GET /api/reports/<report_id>/
   → Wait for status == "completed"

5. Show "Download PDF" button
   GET /api/reports/<report_id>/pdf/
   → Browser downloads PDF file
```

---

## Report Types

### Executive Report
High-level summary for quick reading. Each competitor gets one concise paragraph covering website changes, social activity, and hiring signals together.

### Analyst Report
Full breakdown per competitor including:
- Website changes with analysis
- Social media themes and tone
- Hiring signals and strategic direction
- Key strategic signals (bullet points)
- Raw data tables (job listings, website change details)
