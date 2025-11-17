# 🤖 RAG System - Quick Start Guide

## 📊 What's Being Used

**Vector Database:** PostgreSQL with ArrayField (no Docker needed!)

- Embeddings stored directly in your existing PostgreSQL database
- Model: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- Chunking: 500 characters with 50-character overlap

**LLM:** OpenAI GPT-4o-mini via OpenRouter API

---

## 🚀 Step 1: Ingest Data (One-Time Setup)

```powershell
cd D:\FYP_Backend
.\myenv\Scripts\Activate.ps1
python manage.py ingest_rag_data
```

This will:

- Read all JSON files from `data/honda`, `data/suzukipakistan`, `data/kia-luckymotorcorp`
- Chunk the content intelligently
- Generate embeddings
- Store in PostgreSQL

---

## 📡 Step 2: API Endpoints for Frontend

### **1. Get Competitors List (For Dropdown)**

```http
GET /api/rag/competitors/
Authorization: Token YOUR_TOKEN

Response:
{
  "competitors": [
    {"name": "Honda", "count": 450},
    {"name": "Kia", "count": 384},
    {"name": "Suzuki", "count": 400}
  ]
}
```

### **2. RAG Query (Main Endpoint)**

```http
POST /api/rag/query/
Authorization: Token YOUR_TOKEN
Content-Type: application/json

Body:
{
  "query": "What is the price of Honda BR-V?",
  "competitor_filter": "Honda",  // Optional: "Honda", "Suzuki", "Kia", or null for all
  "top_k": 5  // Optional: number of chunks to retrieve (default: 5)
}

Response:
{
  "query": "What is the price of Honda BR-V?",
  "answer": "Based on the information from Honda's official website...",
  "sources": [
    {
      "id": 123,
      "competitor": "Honda",
      "title": "Honda BR-V – Honda",
      "url": "https://honda.com.pk/hondabrv.php",
      "text": "Honda BRV i-VTEC S (CVT) 6,429,000...",
      "similarity": 0.87,
      "chunk_index": 2,
      "source_file": "https__honda-com-pk_hondabrv-php.json"
    }
  ],
  "metrics": {
    "retrieval_time": 0.145,
    "generation_time": 1.234,
    "total_time": 1.379,
    "chunks_retrieved": 5
  }
}
```

### **3. Semantic Search Only (No AI Generation)**

```http
POST /api/rag/search/
Authorization: Token YOUR_TOKEN
Content-Type: application/json

Body:
{
  "query": "Honda City features",
  "competitor_filter": "Honda",  // Optional
  "top_k": 10
}

Response:
{
  "query": "Honda City features",
  "results": [...],  // Same format as sources above
  "retrieval_time": 0.123,
  "total_results": 10
}
```

### **4. RAG Statistics**

```http
GET /api/rag/stats/
Authorization: Token YOUR_TOKEN

Response:
{
  "total_chunks": 1234,
  "chunks_by_competitor": {
    "Honda": 450,
    "Suzuki": 400,
    "Kia": 384
  },
  "total_queries": 56,
  "avg_retrieval_time": 0.125,
  "avg_generation_time": 1.234,
  "avg_total_time": 1.359
}
```

### **5. Query History**

```http
GET /api/rag/history/?limit=20
Authorization: Token YOUR_TOKEN

Response:
{
  "queries": [
    {
      "id": 1,
      "query": "...",
      "answer": "...",
      "created_at": "2025-11-16T19:30:00",
      "metrics": {...}
    }
  ]
}
```

---

## 🎨 Frontend Implementation Example

### **React Component Example:**

```jsx
import { useState, useEffect } from "react";

function RAGChat() {
  const [competitors, setCompetitors] = useState([]);
  const [selectedCompetitor, setSelectedCompetitor] = useState("all");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  // Fetch competitors for dropdown
  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/rag/competitors/", {
      headers: {
        Authorization: `Token ${YOUR_TOKEN}`,
      },
    })
      .then((res) => res.json())
      .then((data) => setCompetitors(data.competitors));
  }, []);

  const handleQuery = async () => {
    setLoading(true);

    const body = {
      query: query,
      top_k: 5,
    };

    // Add competitor filter if not "all"
    if (selectedCompetitor !== "all") {
      body.competitor_filter = selectedCompetitor;
    }

    const response = await fetch("http://127.0.0.1:8000/api/rag/query/", {
      method: "POST",
      headers: {
        Authorization: `Token ${YOUR_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    setAnswer(data);
    setLoading(false);
  };

  return (
    <div>
      <h2>Ask About Vehicles</h2>

      {/* Competitor Dropdown */}
      <select
        value={selectedCompetitor}
        onChange={(e) => setSelectedCompetitor(e.target.value)}
      >
        <option value="all">All Competitors</option>
        {competitors.map((comp) => (
          <option key={comp.name} value={comp.name}>
            {comp.name} ({comp.count} documents)
          </option>
        ))}
      </select>

      {/* Query Input */}
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask a question..."
      />

      <button onClick={handleQuery} disabled={loading}>
        {loading ? "Searching..." : "Ask"}
      </button>

      {/* Display Answer */}
      {answer && (
        <div>
          <h3>Answer:</h3>
          <p>{answer.answer}</p>

          <h4>Sources:</h4>
          <ul>
            {answer.sources.map((source) => (
              <li key={source.id}>
                <strong>
                  {source.competitor} - {source.title}
                </strong>
                <br />
                Similarity: {(source.similarity * 100).toFixed(1)}%
                <br />
                <a href={source.url} target="_blank">
                  View Source
                </a>
              </li>
            ))}
          </ul>

          <small>
            Retrieved in {answer.metrics.retrieval_time}s | Generated in{" "}
            {answer.metrics.generation_time}s
          </small>
        </div>
      )}
    </div>
  );
}
```

---

## 🔧 How the Competitor Filter Works

1. **Frontend sends query with optional `competitor_filter`:**

   ```json
   {
     "query": "What is the price?",
     "competitor_filter": "Honda" // or "Suzuki", "Kia", or null/omit for all
   }
   ```

2. **Backend filters embeddings:**

   - If `competitor_filter` = `"Honda"` → searches only Honda chunks
   - If `competitor_filter` = `null` or omitted → searches all chunks
   - Uses case-insensitive matching

3. **RAG Service returns:**
   - Top matching chunks from selected competitor(s)
   - AI-generated answer based on those chunks
   - Source attribution showing which competitor the info came from

---

## 📝 Testing with Postman

**Test 1: Query All Competitors**

```http
POST http://127.0.0.1:8000/api/rag/query/
Headers:
  Authorization: Token YOUR_TOKEN
  Content-Type: application/json

Body:
{
  "query": "Compare prices of all SUVs"
}
```

**Test 2: Query Only Honda**

```http
POST http://127.0.0.1:8000/api/rag/query/
Headers:
  Authorization: Token YOUR_TOKEN
  Content-Type: application/json

Body:
{
  "query": "What are Honda BR-V features?",
  "competitor_filter": "Honda"
}
```

**Test 3: Get Dropdown Options**

```http
GET http://127.0.0.1:8000/api/rag/competitors/
Headers:
  Authorization: Token YOUR_TOKEN
```

---

## ✅ Summary

- ✅ **No Docker needed** - uses PostgreSQL directly
- ✅ **Competitor dropdown** - `/api/rag/competitors/` endpoint
- ✅ **Filtered queries** - pass `competitor_filter` in request body
- ✅ **Smart chunking** - 500 char chunks with overlap
- ✅ **Fast retrieval** - in-memory cosine similarity
- ✅ **GPT-4o-mini** - generates contextual answers
- ✅ **Source attribution** - shows which chunks were used

Ready to test! 🚀
