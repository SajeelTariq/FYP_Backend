# TrackRival — Alerts & Email Notification System

## Overview

The alerts system provides two delivery mechanisms:
- **Alerts Page (UI)** — User opens the Alerts page, API returns recent alerts from DB
- **Email** — Automatically sent after each cron job runs (optional, user sets their own email)

### Alert Types

| Type | Trigger | Cron |
|---|---|---|
| `website_change` | Significant HTML changes on competitor pages | 2 AM daily |
| `new_page` | New URL discovered on competitor website | 2 AM daily |
| `new_job` | New job posting detected on LinkedIn | 3 AM daily |
| `follower_change` | LinkedIn followers/employees ≥5% change | 3 AM daily |

---

## RBAC

`RolePermission` model now includes `alerts` field. Role create karte waqt admin Alerts page ka access toggle kar sakta hai — same as Dashboard, Reports etc.

`GET /api/accounts/me/permissions/` now returns:
```json
{
  "dashboard": true,
  "competitors": true,
  "ai_assistant": true,
  "reports": true,
  "settings": true,
  "alerts": true,
  "user_type": "super_admin"
}
```

---

## APIs

### 1. Get Alert Preference
```
GET /api/accounts/me/alert-preference/
```

**cURL:**
```bash
curl -X GET http://localhost:8000/api/accounts/me/alert-preference/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "alert_email": "user@gmail.com",
  "notify_website_changes": true,
  "notify_new_jobs": true,
  "notify_follower_change": true,
  "notify_new_pages": true,
  "updated_at": "2026-05-12T10:00:00Z"
}
```

---

### 2. Update Alert Preference
```
PATCH /api/accounts/me/alert-preference/
```

All fields are optional — send only what you want to update.

**cURL:**
```bash
curl -X PATCH http://localhost:8000/api/accounts/me/alert-preference/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_email": "user@gmail.com",
    "notify_website_changes": true,
    "notify_new_jobs": false,
    "notify_follower_change": true,
    "notify_new_pages": true
  }'
```

**Notes:**
- `alert_email` is optional — if left blank, no email will be sent (alerts still appear on page)
- Each toggle independently controls both UI display and email delivery
- `super_admin` always has full access

---

### 3. Get Alerts List (for Alerts Page UI)
```
GET /api/accounts/me/alerts/
```

**Query Params:**

| Param | Default | Options |
|---|---|---|
| `days` | `7` | `1–30` |
| `type` | `all` | `all`, `website_changes`, `new_pages`, `new_jobs`, `follower_change` |

**cURL — All alerts (last 7 days):**
```bash
curl -X GET "http://localhost:8000/api/accounts/me/alerts/?days=7" \
  -H "Authorization: Token YOUR_TOKEN"
```

**cURL — Specific type:**
```bash
curl -X GET "http://localhost:8000/api/accounts/me/alerts/?days=30&type=new_jobs" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response:**
```json
{
  "count": 3,
  "days": 7,
  "alerts": [
    {
      "type": "website_change",
      "title": "Honda Pakistan — Website Change",
      "description": "Honda reduced the City 1.5L price by PKR 50,000 and introduced 0% markup financing.",
      "meta": {
        "url": "https://www.honda.com.pk/pricing",
        "change_type": "modified",
        "added_lines": 10,
        "removed_lines": 5
      },
      "competitor": "Honda Pakistan",
      "timestamp": "2026-05-12T10:00:00Z"
    },
    {
      "type": "new_page",
      "title": "Kia Pakistan — New Page Detected",
      "description": "New page discovered: https://www.kia.com/pk/ev6",
      "meta": {
        "url": "https://www.kia.com/pk/ev6"
      },
      "competitor": "Kia Pakistan",
      "timestamp": "2026-05-11T08:00:00Z"
    },
    {
      "type": "new_job",
      "title": "Suzuki Pakistan — New Job Posted",
      "description": "Regional Sales Manager · Lahore, Pakistan · Senior",
      "meta": {
        "job_title": "Regional Sales Manager",
        "location": "Lahore, Pakistan",
        "seniority": "Senior",
        "employment_type": "Full-time",
        "job_url": "https://www.linkedin.com/jobs/..."
      },
      "competitor": "Suzuki Pakistan",
      "timestamp": "2026-05-10T03:00:00Z"
    },
    {
      "type": "follower_change",
      "title": "Honda Pakistan — LinkedIn Activity Spike",
      "description": "Followers +24.0% · Employees +4.0%",
      "meta": {
        "follower_count_old": 10000,
        "follower_count_new": 12400,
        "follower_pct": 24.0,
        "employee_count_old": 500,
        "employee_count_new": 520,
        "employee_pct": 4.0
      },
      "competitor": "Honda Pakistan",
      "timestamp": "2026-05-12T03:00:00Z"
    }
  ]
}
```

**Frontend usage:**
- Card view: use `title` + `description` + `timestamp` + `type` (for icon/color)
- Detail modal on click: use `meta` object

**Alert type → UI color/icon:**
```
website_change   → red   / globe icon
new_page         → green / plus icon
new_job          → blue  / briefcase icon
follower_change  → purple/ trending icon
```

---

### 4. Update Role Alerts Permission
```
PATCH /api/accounts/roles/{id}/permissions/
```

**cURL:**
```bash
curl -X PATCH http://localhost:8000/api/accounts/roles/1/permissions/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"alerts": true}'
```

---

### 5. Test Email (Development Only)
```
POST /api/accounts/me/alert-preference/test-email/
```

Manually triggers email dispatch. Uses last 25 hours of data.

**cURL:**
```bash
curl -X POST http://localhost:8000/api/accounts/me/alert-preference/test-email/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "all"}'
```

**`type` options:**
- `"all"` — all 4 email types
- `"website_changes"` — significant page changes only
- `"new_pages"` — new pages only
- `"new_jobs"` — job postings only
- `"follower_change"` — LinkedIn spikes only

**Response:**
```json
{
  "status": "success",
  "message": "Alert emails triggered: all"
}
```

---

## Email Behavior

| Scenario | Email Sent? | Alerts Page? |
|---|---|---|
| `alert_email` set + toggle ON | ✅ Yes | ✅ Yes |
| `alert_email` blank + toggle ON | ❌ No | ✅ Yes |
| `alert_email` set + toggle OFF | ❌ No | ❌ No |
| No AlertPreference record | ❌ No | ❌ No |

### Email Windows
- **Email service** → last 25 hours (runs after cron, sends today's data only)
- **Alerts page API** → last 7 days default, up to 30 days

### Email Schedule
```
2:00 AM → run_daily_monitoring  → send_website_change_alerts()
                                  send_new_pages_alerts()
3:00 AM → run_linkedin_monitoring → send_job_alerts()
                                    send_follower_change_alerts()
```

---

## Environment Variables

Add to `.env`:
```
SENDGRID_API_KEY=SG.your-api-key-here
DEFAULT_FROM_EMAIL=TrackRival <your-verified-sender@gmail.com>
```

---

## Files Changed

| File | Change |
|---|---|
| `apps/accounts/models.py` | `alerts` field added to `RolePermission`; new `AlertPreference` model |
| `apps/accounts/serializers.py` | `AlertPreferenceSerializer` added; `alerts` field in `RolePermissionSerializer` |
| `apps/accounts/views.py` | `AlertPreferenceView`, `AlertsListView`, `TestAlertEmailView` added; `MyPermissionsView` updated |
| `apps/accounts/urls.py` | 3 new URL patterns added |
| `apps/accounts/email_service.py` | New file — all email sending logic |
| `config/settings.py` | SendGrid config + SSL fix added |
| `apps/scraping/tasks.py` | Email hook at end of `run_daily_monitoring` |
| `apps/social_media/tasks.py` | Email hook at end of `run_linkedin_monitoring` |
| `requirements.txt` | `django-sendgrid-v5`, `sendgrid`, `python-http-client` added |
| `requirements_server.txt` | Same packages added |
| `apps/accounts/migrations/0002_*` | Migration for new fields/model |
