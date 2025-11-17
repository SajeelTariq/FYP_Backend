# RAG API Testing Guide (ChromaDB + Hybrid Retrieval)

## Setup Complete! ✅

Your RAG system has been migrated to ChromaDB with **hybrid retrieval** (Dense + BM25).

### What Changed:

- ✅ Embeddings now stored in ChromaDB (not PostgreSQL)
- ✅ Hybrid retrieval: Dense vectors (semantic) + BM25 (keyword matching)
- ✅ Better accuracy with reciprocal rank fusion
- ✅ All competitor filtering still works

---

## API Endpoints

Base URL: `http://127.0.0.1:8000/api/rag/`

**Authentication Required:** Include `Authorization: Token <your_token>` header in all requests.

---

### 1. Get Your Auth Token

**POST** `/api/auth/login/`

```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**

```json
{
  "token": "your_auth_token_here"
}
```

---

### 2. RAG Query (Full Pipeline)

**POST** `/api/rag/query/`

**Headers:**

```
Authorization: Token <your_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "query": "Tell me about Honda BR-V features and price",
  "top_k": 5,
  "competitor_filter": "honda"
}
```

**Parameters:**

- `query` (required): Your question
- `top_k` (optional): Number of chunks to retrieve (default: 5, max: 20)
- `competitor_filter` (optional): Filter by competitor - options: `"honda"`, `"suzuki"`, `"kia"`, or `"all"` (default)

**Response:**

```json
{
  "query": "Tell me about Honda BR-V features and price",
  "answer": "The Honda BR-V is available in Pakistan with...",
  "retrieved_chunks": [
    {
      "text": "Honda BR-V features include...",
      "metadata": {
        "competitor_name": "honda",
        "url": "https://honda.com.pk/hondabrv",
        "title": "Honda BR-V",
        "chunk_index": 0
      },
      "score": 0.89
    }
  ],
  "retrieval_time": 0.234,
  "generation_time": 1.567,
  "total_time": 1.801,
  "top_k": 5,
  "competitor_filter": "honda"
}
```

---

### 3. Semantic Search Only (No Answer Generation)

**POST** `/api/rag/search/`

**Headers:**

```
Authorization: Token <your_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "query": "Honda Civic specifications",
  "top_k": 10,
  "competitor_filter": "all"
}
```

**Response:**

```json
{
  "query": "Honda Civic specifications",
  "results": [
    {
      "id": "honda_civic_0",
      "text": "Honda Civic Type R features...",
      "metadata": {
        "competitor_name": "honda",
        "url": "https://honda.com.pk/civic",
        "title": "Honda Civic"
      },
      "fusion_score": 0.92
    }
  ],
  "retrieval_time": 0.156,
  "total_results": 10
}
```

---

### 4. Get System Statistics

**GET** `/api/rag/stats/`

**Headers:**

```
Authorization: Token <your_token>
```

**Response:**

```json
{
  "total_chunks": 1271,
  "competitor_chunks": {
    "honda": 348,
    "suzuki": 290,
    "kia": 633
  },
  "embedding_dimension": 384,
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "retrieval_method": "hybrid (dense + BM25)",
  "database": "ChromaDB"
}
```

---

### 5. Get Competitors List (for Dropdown)

**GET** `/api/rag/competitors/`

**Headers:**

```
Authorization: Token <your_token>
```

**Response:**

```json
{
  "competitors": [
    {
      "name": "All Competitors",
      "value": "all",
      "chunk_count": 1271
    },
    {
      "name": "Honda",
      "value": "honda",
      "chunk_count": 348
    },
    {
      "name": "Suzuki",
      "value": "suzuki",
      "chunk_count": 290
    },
    {
      "name": "Kia",
      "value": "kia",
      "chunk_count": 633
    }
  ]
}
```

---

## Test Cases

### Test 1: Query Honda BR-V

```json
POST /api/rag/query/
{
  "query": "What are the features and price of Honda BR-V?",
  "competitor_filter": "honda"
}
```

### Test 2: Query All Competitors

```json
POST /api/rag/query/
{
  "query": "Which SUVs are available under 8 million PKR?",
  "competitor_filter": "all",
  "top_k": 10
}
```

### Test 3: Search Only (No Generation)

```json
POST /api/rag/search/
{
  "query": "Suzuki Alto price",
  "competitor_filter": "suzuki",
  "top_k": 5
}
```

### Test 4: Hybrid Retrieval Test

```json
POST /api/rag/query/
{
  "query": "Honda Civic Type R specifications",
  "competitor_filter": "honda"
}
```

This should now return better results because hybrid retrieval combines:

- Dense search: Finds semantically similar content
- BM25 search: Finds exact keyword matches
- Fusion: Combines both for best results

---

## Postman Collection Steps

1. **Get Token:**

   - POST `http://127.0.0.1:8000/api/auth/login/`
   - Body: `{"username": "admin", "password": "admin123"}`
   - Copy the token from response

2. **Set Authorization:**

   - In Postman, go to Authorization tab
   - Type: `Bearer Token` or add header manually
   - Key: `Authorization`
   - Value: `Token <paste_your_token>`

3. **Test RAG Query:**

   - POST `http://127.0.0.1:8000/api/rag/query/`
   - Body: JSON with query and filters
   - Check response for answer and retrieved chunks

4. **Test Stats:**
   - GET `http://127.0.0.1:8000/api/rag/stats/`
   - Should show 1271 total chunks

---

## Hybrid Retrieval Explained

Your RAG system now uses **two retrieval methods simultaneously**:

### 1. Dense Vector Search (Semantic)

- Uses sentence-transformers embeddings
- Finds contextually similar content
- Good for: "Tell me about SUV features" → finds content about SUVs even without exact word match

### 2. BM25 Sparse Retrieval (Keyword)

- Classical IR algorithm (like search engines)
- Finds exact keyword matches
- Good for: "Honda BR-V price" → finds exact product and price info

### 3. Reciprocal Rank Fusion (RRF)

- Combines results from both methods
- Gives higher rank to documents that appear in both result sets
- More accurate than using just one method

**Result:** Better accuracy, especially for queries that need both semantic understanding AND exact keyword matching!

---

## Re-ingest Data (if needed)

If you need to re-ingest the data:

```bash
python manage.py ingest_chromadb --force
```

This will:

1. Clear existing ChromaDB data
2. Re-ingest all JSON files from `data/` folder
3. Rebuild BM25 index

---

## Troubleshooting

### Issue: "No module named 'chromadb'"

```bash
pip install chromadb rank-bm25
```

### Issue: ChromaDB data missing

```bash
python manage.py ingest_chromadb
```

### Issue: Server won't start

```bash
.\myenv\Scripts\activate
python manage.py runserver
```

---

## Next Steps

After testing in Postman:

1. ✅ Verify hybrid retrieval is working (check fusion_score in results)
2. ✅ Test with different competitor filters
3. ✅ Compare accuracy with previous PostgreSQL version
4. 🔄 Ready to migrate to Milvus standalone when needed

---

**Note:** ChromaDB stores data in `chroma_db/` folder (already in .gitignore)
