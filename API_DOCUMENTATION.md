# API Documentation - Competitor Monitoring System

## Base URL

```
http://localhost:8000/api/monitoring/
```

## Authentication

All endpoints (except registration and login) require Token Authentication.

### Headers

```
Authorization: Token <your_token_here>
Content-Type: application/json
```

---

## Authentication Endpoints

### 1. Register User

**POST** `/api/monitoring/auth/register/`

**Request Body:**

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepass123",
  "password_confirm": "securepass123"
}
```

**Response (201 Created):**

```json
{
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "date_joined": "2025-11-16T10:00:00Z"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

### 2. Login

**POST** `/api/monitoring/auth/login/`

**Request Body:**

```json
{
  "username": "john_doe",
  "password": "securepass123"
}
```

**Response (200 OK):**

```json
{
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "date_joined": "2025-11-16T10:00:00Z"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

---

### 3. Logout

**POST** `/api/monitoring/auth/logout/`

**Headers Required:** `Authorization: Token <token>`

**Response (200 OK):**

```json
{
  "message": "Successfully logged out"
}
```

---

## Competitor Management Endpoints

### 1. List All Competitors

**GET** `/api/monitoring/competitors/`

**Headers:** `Authorization: Token <token>`

**Description:** Retrieve all competitors for the authenticated user (excludes soft-deleted competitors).

**Response (200 OK):**

```json
[
  {
    "id": 1,
    "name": "Tech Startup Inc",
    "website_base_url": "https://techstartup.com",
    "linkedin_url": "https://linkedin.com/company/techstartup",
    "facebook_url": "https://facebook.com/techstartup",
    "instagram_url": "https://instagram.com/techstartup",
    "twitter_url": "https://twitter.com/techstartup",
    "is_deleted": false,
    "created_at": "2025-11-16T10:00:00Z",
    "updated_at": "2025-11-16T10:00:00Z"
  },
  {
    "id": 2,
    "name": "Competitor B",
    "website_base_url": null,
    "linkedin_url": "https://linkedin.com/company/competitorb",
    "facebook_url": "https://facebook.com/competitorb",
    "instagram_url": null,
    "twitter_url": null,
    "is_deleted": false,
    "created_at": "2025-11-17T11:00:00Z",
    "updated_at": "2025-11-17T11:00:00Z"
  }
]
```

---

### 2. Get Single Competitor

**GET** `/api/monitoring/competitors/{id}/`

**Headers:** `Authorization: Token <token>`

**Description:** Retrieve detailed information about a specific competitor.

**Response (200 OK):**

```json
{
  "id": 1,
  "name": "Tech Startup Inc",
  "website_base_url": "https://techstartup.com",
  "linkedin_url": "https://linkedin.com/company/techstartup",
  "facebook_url": "https://facebook.com/techstartup",
  "instagram_url": "https://instagram.com/techstartup",
  "twitter_url": "https://twitter.com/techstartup",
  "is_deleted": false,
  "created_at": "2025-11-16T10:00:00Z",
  "updated_at": "2025-11-16T10:00:00Z"
}
```

**Response (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

---

### 3. Create Competitor

**POST** `/api/monitoring/competitors/`

**Headers:** `Authorization: Token <token>`

**Description:** Create a new competitor or update existing one if URLs match.

**Request Body:**

```json
{
  "name": "Tech Startup Inc",
  "website_base_url": "https://techstartup.com",
  "linkedin_url": "https://linkedin.com/company/techstartup",
  "facebook_url": "https://facebook.com/techstartup",
  "instagram_url": "https://instagram.com/techstartup",
  "twitter_url": "https://twitter.com/techstartup"
}
```

**Note:** At least one URL is required. Empty strings or missing fields are treated as null.

**Response (201 Created) - New Competitor:**

```json
{
  "message": "Competitor created successfully",
  "competitor": {
    "id": 1,
    "name": "Tech Startup Inc",
    "website_base_url": "https://techstartup.com",
    "linkedin_url": "https://linkedin.com/company/techstartup",
    "facebook_url": "https://facebook.com/techstartup",
    "instagram_url": "https://instagram.com/techstartup",
    "twitter_url": "https://twitter.com/techstartup",
    "is_deleted": false,
    "created_at": "2025-11-16T10:00:00Z",
    "updated_at": "2025-11-16T10:00:00Z"
  },
  "created": true
}
```

**Response (200 OK) - Updated Existing:**

```json
{
  "message": "Competitor updated successfully",
  "competitor": {
    "id": 1,
    "name": "Tech Startup Inc",
    "website_base_url": "https://techstartup.com",
    "linkedin_url": "https://linkedin.com/company/techstartup",
    "facebook_url": null,
    "instagram_url": null,
    "twitter_url": null,
    "is_deleted": false,
    "created_at": "2025-11-16T10:00:00Z",
    "updated_at": "2025-11-16T10:35:00Z"
  },
  "created": false
}
```

**Response (400 Bad Request):**

```json
{
  "name": ["This field is required."]
}
```

---

### 4. Full Update Competitor

**PUT** `/api/monitoring/competitors/{id}/`

**Headers:** `Authorization: Token <token>`

**Description:** Completely replace competitor information. All fields must be provided.

**Request Body:**

```json
{
  "name": "Updated Tech Startup Inc",
  "website_base_url": "https://new-techstartup.com",
  "linkedin_url": "https://linkedin.com/company/techstartup",
  "facebook_url": "https://facebook.com/techstartup",
  "instagram_url": "https://instagram.com/techstartup",
  "twitter_url": "https://twitter.com/techstartup"
}
```

**Response (200 OK):**

```json
{
  "message": "Competitor updated successfully",
  "competitor": {
    "id": 1,
    "name": "Updated Tech Startup Inc",
    "website_base_url": "https://new-techstartup.com",
    "linkedin_url": "https://linkedin.com/company/techstartup",
    "facebook_url": "https://facebook.com/techstartup",
    "instagram_url": "https://instagram.com/techstartup",
    "twitter_url": "https://twitter.com/techstartup",
    "is_deleted": false,
    "created_at": "2025-11-16T10:00:00Z",
    "updated_at": "2025-11-17T12:00:00Z"
  }
}
```

---

### 5. Partial Update Competitor

**PATCH** `/api/monitoring/competitors/{id}/`

**Headers:** `Authorization: Token <token>`

**Description:** Update only specific fields of a competitor. Only provide the fields you want to change.

**Request Example 1 - Add LinkedIn URL:**

```json
{
  "linkedin_url": "https://linkedin.com/company/techstartup"
}
```

**Request Example 2 - Update Name and Add Instagram:**

```json
{
  "name": "Tech Startup Inc Updated",
  "instagram_url": "https://instagram.com/techstartup"
}
```

**Request Example 3 - Remove URL (set to null):**

```json
{
  "facebook_url": ""
}
```

**Response (200 OK):**

```json
{
  "message": "Competitor updated successfully",
  "competitor": {
    "id": 1,
    "name": "Tech Startup Inc Updated",
    "website_base_url": "https://techstartup.com",
    "linkedin_url": "https://linkedin.com/company/techstartup",
    "facebook_url": null,
    "instagram_url": "https://instagram.com/techstartup",
    "twitter_url": null,
    "is_deleted": false,
    "created_at": "2025-11-16T10:00:00Z",
    "updated_at": "2025-11-17T12:15:00Z"
  }
}
```

**Response (400 Bad Request):**

```json
{
  "error": "No valid fields provided for update"
}
```

---

### 6. Delete Competitor (Soft Delete)

**DELETE** `/api/monitoring/competitors/{id}/`

**Headers:** `Authorization: Token <token>`

**Description:** Soft delete a competitor (sets `is_deleted=True` and `deleted_at` timestamp).

**Response (200 OK):**

```json
{
  "message": "Competitor deleted successfully"
}
```

**Response (404 Not Found):**

```json
{
  "detail": "Not found."
}
```

---

### Frontend Implementation Example

```javascript
// Fetch all competitors
const fetchCompetitors = async () => {
  const response = await fetch(
    "http://localhost:8000/api/monitoring/competitors/",
    {
      method: "GET",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json",
      },
    }
  );
  return await response.json();
};

// Edit competitor (partial update - only changed fields)
const editCompetitor = async (competitorId, updatedFields) => {
  const response = await fetch(
    `http://localhost:8000/api/monitoring/competitors/${competitorId}/`,
    {
      method: "PATCH",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(updatedFields),
    }
  );
  return await response.json();
};

// Delete competitor
const deleteCompetitor = async (competitorId) => {
  const response = await fetch(
    `http://localhost:8000/api/monitoring/competitors/${competitorId}/`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Token ${userToken}`,
        "Content-Type": "application/json",
      },
    }
  );
  return await response.json();
};

// Example usage
(async () => {
  // Get all competitors
  const competitors = await fetchCompetitors();
  console.log("All Competitors:", competitors);

  // Edit a competitor (add LinkedIn URL)
  const updated = await editCompetitor(1, {
    linkedin_url: "https://linkedin.com/company/newurl",
  });
  console.log("Updated:", updated);

  // Delete a competitor
  const deleted = await deleteCompetitor(2);
  console.log("Deleted:", deleted);
})();
```

---

## Scraping Endpoints (Async Tasks)

These endpoints trigger asynchronous Celery tasks that run your scraping scripts.

### 1. Extract Links from Website

**POST** `/api/monitoring/competitors/{id}/extract_links/`

**Headers:** `Authorization: Token <token>`

**Description:** Extracts all subpage links from competitor's website using Firecrawl API and stores them in `extracted_links` table.

**Response (202 Accepted):**

```json
{
  "status": "Task started",
  "message": "Link extraction started for Tech Startup Inc",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "competitor": "Tech Startup Inc"
}
```

---

### 2. Scrape HTML Content

**POST** `/api/monitoring/competitors/{id}/scrape_html/`

**Headers:** `Authorization: Token <token>`

**Request Body (Optional):**

```json
{
  "use_filtered_links": false
}
```

**Description:** Scrapes HTML content from all links using Playwright (headless browser) and stores in `competitor_html` table. Set `use_filtered_links: true` to scrape only filtered links instead of all extracted links.

**Response (202 Accepted):**

```json
{
  "status": "Task started",
  "message": "HTML scraping started for Tech Startup Inc",
  "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "competitor": "Tech Startup Inc",
  "using_filtered_links": false
}
```

---

### 3. Extract Metadata for RAG

**POST** `/api/monitoring/competitors/{id}/extract_metadata/`

**Headers:** `Authorization: Token <token>`

**Description:** Processes scraped HTML content to extract clean text and metadata for the RAG system. Stores in `competitor_metadata` table.

**Response (202 Accepted):**

```json
{
  "status": "Task started",
  "message": "Metadata extraction started for Tech Startup Inc",
  "task_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "competitor": "Tech Startup Inc"
}
```

---

### 4. Run Full Scraping Pipeline

**POST** `/api/monitoring/competitors/{id}/run_full_pipeline/`

**Headers:** `Authorization: Token <token>`

**Request Body (Optional):**

```json
{
  "use_filtered_links": false
}
```

**Description:** Runs the complete scraping pipeline in sequence:

1. Extract links (if not using filtered)
2. Scrape HTML content
3. Extract metadata for RAG

**Response (202 Accepted):**

```json
{
  "status": "Task started",
  "message": "Full scraping pipeline started for Tech Startup Inc",
  "task_id": "d4e5f6a7-b8c9-0123-def0-123456789abc",
  "competitor": "Tech Startup Inc",
  "using_filtered_links": false
}
```

---

## Data Storage Endpoints

### 1. Store Extracted Links

**POST** `/api/monitoring/extracted-links/`

**Request Body:**

```json
{
  "competitor": 1,
  "links": [
    "https://techstartup.com/about",
    "https://techstartup.com/products",
    "https://techstartup.com/contact"
  ]
}
```

---

### 2. Store Filtered Links

**POST** `/api/monitoring/filtered-links/`

**Request Body:**

```json
{
  "competitor": 1,
  "links": [
    "https://techstartup.com/products",
    "https://techstartup.com/pricing"
  ]
}
```

---

### 3. Store Daily Scraper Links

**POST** `/api/monitoring/daily-scraper-links/`

**Request Body:**

```json
{
  "competitor": 1,
  "links": ["https://techstartup.com/blog"]
}
```

---

### 4. Store HTML Content

**POST** `/api/monitoring/html-content/`

**Request Body:**

```json
{
  "competitor": 1,
  "url": "https://techstartup.com/about",
  "html_content": "<!DOCTYPE html><html>...</html>"
}
```

---

### 5. Store Metadata for RAG

**POST** `/api/monitoring/metadata/`

**Request Body:**

```json
{
  "competitor": 1,
  "url": "https://techstartup.com/about",
  "metadata": {
    "title": "About Us - Tech Startup",
    "description": "Learn about our company",
    "content": "Extracted and processed content...",
    "keywords": ["tech", "startup", "innovation"]
  }
}
```

---

### 6. Get HTML Content

**GET** `/api/monitoring/html-content/?competitor={id}`

Returns list of HTML content for a specific competitor.

---

### 7. Get Metadata

**GET** `/api/monitoring/metadata/?competitor={id}`

Returns metadata for RAG system.

---

## Example Usage with Python

### Basic API Usage

```python
import requests

BASE_URL = "http://localhost:8000/api/monitoring"

# 1. Register
response = requests.post(f"{BASE_URL}/auth/register/", json={
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepass123",
    "password_confirm": "securepass123"
})
token = response.json()['token']

# 2. Headers for authenticated requests
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}

# 3. Add competitor
response = requests.post(f"{BASE_URL}/competitors/",
    headers=headers,
    json={
        "name": "Tech Startup Inc",
        "website_base_url": "https://techstartup.com",
        "linkedin_url": "https://linkedin.com/company/techstartup"
    }
)
competitor_id = response.json()['competitor']['id']

# 4. Store extracted links (manual)
requests.post(f"{BASE_URL}/extracted-links/",
    headers=headers,
    json={
        "competitor": competitor_id,
        "links": ["https://techstartup.com/about", "https://techstartup.com/products"]
    }
)

# 5. Store HTML (manual)
requests.post(f"{BASE_URL}/html-content/",
    headers=headers,
    json={
        "competitor": competitor_id,
        "url": "https://techstartup.com/about",
        "html_content": "<html>...</html>"
    }
)

# 6. Store metadata for RAG (manual)
requests.post(f"{BASE_URL}/metadata/",
    headers=headers,
    json={
        "competitor": competitor_id,
        "url": "https://techstartup.com/about",
        "metadata": {
            "title": "About Us",
            "content": "Company information..."
        }
    }
)
```

---

### Automated Scraping Pipeline (Recommended)

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/monitoring"

# 1. Login
response = requests.post(f"{BASE_URL}/auth/login/", json={
    "username": "john_doe",
    "password": "securepass123"
})
token = response.json()['token']
headers = {"Authorization": f"Token {token}"}

# 2. Add competitor
response = requests.post(f"{BASE_URL}/competitors/",
    headers=headers,
    json={
        "name": "Honda Pakistan",
        "website_base_url": "https://honda.com.pk"
    }
)
competitor_id = response.json()['competitor']['id']
print(f"✅ Competitor created with ID: {competitor_id}")

# 3. Run full scraping pipeline (automated - uses your scripts!)
response = requests.post(
    f"{BASE_URL}/competitors/{competitor_id}/run_full_pipeline/",
    headers=headers,
    json={"use_filtered_links": False}
)
task_id = response.json()['task_id']
print(f"🚀 Scraping pipeline started. Task ID: {task_id}")

# 4. The pipeline will automatically:
#    a) Extract all links using Firecrawl API (Links_extractor.py logic)
#    b) Scrape HTML from all links using Playwright (Scrape_HTML.py logic)
#    c) Extract metadata for RAG (json_of_html.py logic)

# 5. Wait for completion, then retrieve data
time.sleep(60)  # Adjust based on website size

# Get extracted links
links_response = requests.get(
    f"{BASE_URL}/extracted-links/?competitor={competitor_id}",
    headers=headers
)
print(f"📋 Extracted links: {links_response.json()}")

# Get HTML content
html_response = requests.get(
    f"{BASE_URL}/html-content/?competitor={competitor_id}",
    headers=headers
)
print(f"📄 HTML pages scraped: {len(html_response.json())}")

# Get metadata for RAG
metadata_response = requests.get(
    f"{BASE_URL}/metadata/?competitor={competitor_id}",
    headers=headers
)
print(f"🤖 Metadata entries for RAG: {len(metadata_response.json())}")
```

---

### Individual Task Triggers

```python
# Run tasks individually instead of full pipeline

# 1. Extract links only
response = requests.post(
    f"{BASE_URL}/competitors/{competitor_id}/extract_links/",
    headers=headers
)
print(f"Task ID: {response.json()['task_id']}")

# 2. Scrape HTML only (after links are extracted)
response = requests.post(
    f"{BASE_URL}/competitors/{competitor_id}/scrape_html/",
    headers=headers,
    json={"use_filtered_links": False}
)
print(f"Task ID: {response.json()['task_id']}")

# 3. Extract metadata only (after HTML is scraped)
response = requests.post(
    f"{BASE_URL}/competitors/{competitor_id}/extract_metadata/",
    headers=headers
)
print(f"Task ID: {response.json()['task_id']}")
```

---

## Database Schema

The system uses the following models as shown in your diagram:

- **users**: Django's built-in User model
- **competitors**: Stores competitor information with social media links
- **extracted_links**: Stores all extracted URLs from website
- **filtered_links**: Stores filtered/relevant URLs
- **daily_scraper_links**: Stores URLs for daily scraping
- **user_competitors**: Junction table (handled by ForeignKey)

---

## Next Steps

1. Run migrations: `python manage.py makemigrations && python manage.py migrate`
2. Create superuser: `python manage.py createsuperuser`
3. Start server: `python manage.py runserver`
4. Test endpoints using Postman or the Python example above
