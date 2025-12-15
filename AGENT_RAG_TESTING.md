# Agent-Based RAG System - Testing Guide

## 🤖 System Architecture

Your RAG system now uses an **Agent-Based Architecture** with intelligent query routing:

```
User Query → Orchestrator Agent → [Detects Intent] → Routes to:
                                                       ├─ GeneralQueryAgent (product/feature queries)
                                                       └─ HTMLDiffAgent (change/difference queries)
```

### Agents:

1. **OrchestratorAgent**: Analyzes query intent and routes to appropriate agent
2. **GeneralQueryAgent**: Handles standard product/feature/price queries (existing RAG)
3. **HTMLDiffAgent**: Handles website change/difference tracking queries (new!)

---

## 📋 Sample Queries for Postman Testing

### Base URL

```
http://127.0.0.1:8000/api/rag/query/
```

### Authentication

All requests require:

```
Authorization: Token <your_token>
Content-Type: application/json
```

---

## ✅ Test Case 1: General Product Queries (→ GeneralQueryAgent)

These queries will be routed to the **GeneralQueryAgent** (existing RAG functionality):

### Query 1.1: Product Features

```json
POST http://127.0.0.1:8000/api/rag/query/

{
  "query": "What are the vehicles suzuki currently selling?",
  "competitor_filter": "suzuki",
  "top_k": 5
}
```

### Query 1.2: Price Information

```json
{
  "query": "Tell me about Honda BR-V features and price",
  "competitor_filter": "honda",
  "top_k": 5
}
```

### Query 1.3: Specifications

```json
{
  "query": "What are the engine specifications of Kia Sportage?",
  "competitor_filter": "kia",
  "top_k": 5
}
```

### Query 1.4: Comparison

```json
{
  "query": "Which SUVs are available under 8 million PKR?",
  "competitor_filter": "all",
  "top_k": 10
}
```

### Query 1.5: All Competitors

```json
{
  "query": "List all available Honda vehicles in Pakistan",
  "competitor_filter": "honda",
  "top_k": 5
}
```

**Expected Response Structure:**

```json
{
  "query": "What are the vehicles suzuki currently selling?",
  "answer": "Suzuki offers several vehicles including...",
  "retrieved_chunks": [...],
  "retrieval_time": 0.234,
  "generation_time": 1.567,
  "total_time": 1.801,
  "agent": {
    "name": "GeneralQuery",
    "type": "general_query",
    "execution_time": 1.805
  },
  "orchestration": {
    "orchestrator": "Orchestrator",
    "selected_agent": "GeneralQuery",
    "detected_intent": "general",
    "routing_time": 0.003
  }
}
```

---

## 🔄 Test Case 2: HTML Difference Queries (→ HTMLDiffAgent)

These queries will be routed to the **HTMLDiffAgent** (website change tracking):

### Query 2.1: Recent Changes

```json
POST http://127.0.0.1:8000/api/rag/query/

{
  "query": "What are the last 2 changes suzuki made in its website?",
  "competitor_filter": "suzuki"
}
```

### Query 2.2: Changes in Time Period

```json
{
  "query": "List all the changes suzuki made in its website in last week",
  "competitor_filter": "suzuki"
}
```

### Query 2.3: Recent Updates

```json
{
  "query": "What updates did Honda make to their website recently?",
  "competitor_filter": "honda"
}
```

### Query 2.4: Modifications Query

```json
{
  "query": "Show me recent modifications on Kia website",
  "competitor_filter": "kia"
}
```

### Query 2.5: What Changed

```json
{
  "query": "What changed on Suzuki's products page in the last month?",
  "competitor_filter": "suzuki"
}
```

### Query 2.6: New Content

```json
{
  "query": "What new content was added to Honda website this week?",
  "competitor_filter": "honda"
}
```

### Query 2.7: Website Differences

```json
{
  "query": "Tell me about the differences in Suzuki website compared to last week",
  "competitor_filter": "suzuki"
}
```

**Expected Response Structure:**

```json
{
  "query": "What are the last 2 changes suzuki made in its website?",
  "answer": "\n**Suzuki Pakistan** (4 changes):\n  1. https://suzukipakistan.com/products: 7 changes (discount pricing section added, price reduced...) (7 days ago)\n  2. https://suzukipakistan.com/pricing: 7 changes (discount pricing section added...) (7 days ago)",
  "total_changes_found": 4,
  "changes": [
    {
      "id": 1,
      "competitor": "Suzuki Pakistan",
      "url": "https://suzukipakistan.com/products",
      "change_type": "modified",
      "detected_at": "2025-12-14T...",
      "is_significant": true,
      "summary": {
        "added_sections": ["discount pricing section", "new features"],
        "removed_sections": [],
        "modified_sections": ["price reduced from $99.99 to $89.99"],
        "total_changes": 7
      },
      "details": [
        {
          "type": "modified",
          "section": "price",
          "old_value": "Price: $99.99",
          "new_value": "Price: $89.99",
          "line_number": 8
        }
      ]
    }
  ],
  "filters_applied": {
    "competitor": "suzuki",
    "time_range_days": 7,
    "limit": 2
  },
  "agent": {
    "name": "HTMLDiffFinder",
    "type": "html_diff_finder",
    "execution_time": 0.045
  },
  "orchestration": {
    "orchestrator": "Orchestrator",
    "selected_agent": "HTMLDiffFinder",
    "detected_intent": "html_diff",
    "routing_time": 0.002
  }
}
```

---

## 🔍 Test Case 3: Edge Cases & Mixed Intent

### Query 3.1: Ambiguous Query (Will go to General)

```json
{
  "query": "Tell me about Suzuki Alto",
  "competitor_filter": "suzuki"
}
```

**Expected:** Routes to **GeneralQueryAgent** (no change keywords)

### Query 3.2: Clear Diff Query

```json
{
  "query": "What's different in Honda website today vs yesterday?",
  "competitor_filter": "honda"
}
```

**Expected:** Routes to **HTMLDiffAgent** (has "different", temporal keywords)

### Query 3.3: Change in Product (Tricky)

```json
{
  "query": "Did the price of Suzuki Alto change?",
  "competitor_filter": "suzuki"
}
```

**Expected:** Routes to **HTMLDiffAgent** (has "change" keyword, temporal context)

---

## 📊 Test Case 4: Agent Statistics

### Get Agent Performance Stats

```
GET http://127.0.0.1:8000/api/rag/agent-stats/
Authorization: Token <your_token>
```

**Expected Response:**

```json
{
  "orchestrator": {
    "agent_name": "Orchestrator",
    "total_executions": 15,
    "success_rate": 100,
    "avg_execution_time": 0.125
  },
  "agents": [
    {
      "agent_name": "HTMLDiffFinder",
      "total_executions": 7,
      "success_rate": 100,
      "avg_execution_time": 0.045
    },
    {
      "agent_name": "GeneralQuery",
      "total_executions": 8,
      "success_rate": 100,
      "avg_execution_time": 1.523
    }
  ]
}
```

---

## 🧪 Complete Testing Workflow

### Step 1: Login and Get Token

```json
POST http://127.0.0.1:8000/api/monitoring/auth/login/

{
  "username": "your_username",
  "password": "your_password"
}
```

### Step 2: Test General Queries (3-5 queries)

Test queries from **Test Case 1** - verify they route to **GeneralQuery** agent

### Step 3: Test HTML Diff Queries (3-5 queries)

Test queries from **Test Case 2** - verify they route to **HTMLDiffFinder** agent

### Step 4: Check Agent Stats

```
GET http://127.0.0.1:8000/api/rag/agent-stats/
```

### Step 5: Verify Routing Logic

Look for `orchestration.detected_intent` in responses:

- `"general"` → GeneralQueryAgent
- `"html_diff"` → HTMLDiffAgent

---

## 🎯 Key Differences to Notice

### General Query Response:

- Has `retrieved_chunks` with semantic search results
- Has `answer` generated by LLM
- Agent name: `"GeneralQuery"`
- Longer execution time (~1-2 seconds)

### HTML Diff Query Response:

- Has `changes` array with HTML differences
- Has `total_changes_found` count
- Has `filters_applied` showing time range
- Agent name: `"HTMLDiffFinder"`
- Faster execution time (~0.05-0.1 seconds)

---

## 🔑 Intent Detection Keywords

The orchestrator detects HTML diff queries using these keywords:

**Change Keywords:**

- change, changes, changed
- modification, modifications, modified
- update, updates, updated
- difference, differences, diff
- altered, removed, added

**Temporal Keywords:**

- last week, last month, yesterday, today
- recent, recently, latest
- in the last, within, since

**Pattern Examples:**

- "What changed..."
- "Show me updates..."
- "List recent modifications..."
- "What was different..."

---

## 📝 Postman Collection Structure

Create a Postman collection with these folders:

```
RAG Agent System
├── Authentication
│   └── Login
├── General Queries (GeneralQueryAgent)
│   ├── Product Features
│   ├── Price Information
│   ├── Specifications
│   └── Comparisons
├── HTML Diff Queries (HTMLDiffAgent)
│   ├── Recent Changes
│   ├── Last N Changes
│   ├── Time-based Changes
│   └── What Changed
├── Edge Cases
│   └── Ambiguous Queries
└── System
    ├── Agent Stats
    ├── RAG Stats
    └── Get Competitors
```

---

## ✅ Success Criteria

1. **General queries** should return product information with `"detected_intent": "general"`
2. **HTML diff queries** should return change information with `"detected_intent": "html_diff"`
3. **Response times**: HTML diff < 0.2s, General query < 3s
4. **Agent stats** should show execution counts for both agents
5. **Error handling** should return clear error messages with agent context

---

## 🐛 Troubleshooting

### Issue: All queries go to GeneralQuery

- Check if HTML diff keywords are in query
- Verify HTMLDiffAgent is registered in orchestrator
- Check orchestrator keyword lists

### Issue: HTML diff returns empty changes

- Run: `python manage.py add_dummy_html_tracking`
- Verify user has competitors in database
- Check time range filters

### Issue: Agent not found error

- Restart Django server
- Verify agent files are in `apps/rag/agents/` directory
- Check import statements in views_chromadb.py

---

## 🚀 Next Steps

After testing:

1. Monitor agent stats to see routing distribution
2. Fine-tune intent detection keywords if needed
3. Add more specialized agents (e.g., ComparisonAgent, PriceTrackingAgent)
4. Implement agent fallback strategies
5. Add logging for agent decisions

---

**Happy Testing! 🎉**
