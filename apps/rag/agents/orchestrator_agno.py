"""
Orchestrator Agent - Routes queries to appropriate specialized agents.
"""
import time
import re
from typing import Dict, Any

from .general_query_agent import GeneralQueryAgent
from .html_diff_agent import WebsiteChangesAgent
from .news_agent import NewsAgent


class OrchestratorAgent:
    """
    Orchestrator that routes queries to one of three specialized agents:
      - GeneralQueryAgent    → product/feature/pricing questions (ChromaDB RAG)
      - WebsiteChangesAgent  → website change / diff questions (HTMLDifference DB)
      - NewsAgent            → competitor news questions (NewsArticle DB)

    Intent is detected via keyword scoring — fast and deterministic.
    The actual intelligence lives inside each agent's tool-calling loop.
    """

    # Keywords that strongly suggest a website-changes query
    _WEBSITE_CHANGE_KEYWORDS = [
        "change", "changes", "changed", "modification", "modifications", "modified",
        "update", "updates", "updated", "difference", "differences", "diff",
        "what was", "what were", "what happened", "recent", "recently",
        "latest", "added", "removed", "altered",
        "website change", "page change", "content change",
        "before", "after", "compared to",
    ]

    # Keywords that strongly suggest a news query
    _NEWS_KEYWORDS = [
        "news", "article", "articles", "headline", "headlines", "press",
        "media", "announcement", "announcements", "published", "reported",
        "journalist", "coverage", "story", "stories", "publication",
        "mention", "mentions", "mentioned",
    ]

    # Temporal keywords — boost both website-change and news scores
    _TEMPORAL_KEYWORDS = [
        "last week", "last month", "yesterday", "today",
        "past week", "past month", "recent days", "recently",
        "in the last", "within", "since", "ago",
    ]

    # Regex patterns that strongly indicate a website-change query
    _WEBSITE_CHANGE_PATTERNS = [
        r"what\s+(changed|updated|modified)",
        r"(changes|updates|modifications)\s+(in|on|to)",
        r"last\s+\d+\s+(change|update|modification)",
        r"(show|list|tell)\s+.*(change|update|modification)",
        r"(difference|diff)\s+(between|from)",
    ]

    def __init__(self, api_key: str = None):
        self.name = "Orchestrator"
        self.api_key = api_key
        self.execution_history = []

        self.general_agent = GeneralQueryAgent(api_key=api_key)
        self.website_changes_agent = WebsiteChangesAgent(api_key=api_key)
        self.news_agent = NewsAgent(api_key=api_key)

        self.agents = [self.general_agent, self.website_changes_agent, self.news_agent]

    def _detect_query_intent(self, query: str) -> str:
        """
        Score the query against three intent buckets and return the winning one.
        Returns: 'website_changes' | 'news' | 'general'
        """
        q = query.lower()

        website_score = 0
        news_score = 0

        for kw in self._WEBSITE_CHANGE_KEYWORDS:
            if kw in q:
                website_score += 2

        for kw in self._NEWS_KEYWORDS:
            if kw in q:
                news_score += 3  # news keywords are more specific, weight them higher

        # Temporal keywords boost the leading score
        temporal_boost = sum(3 for kw in self._TEMPORAL_KEYWORDS if kw in q)

        for pattern in self._WEBSITE_CHANGE_PATTERNS:
            if re.search(pattern, q):
                website_score += 3

        # Apply temporal boost to whichever bucket is already leading
        if website_score >= news_score:
            website_score += temporal_boost
        else:
            news_score += temporal_boost

        if website_score >= 3 and website_score >= news_score:
            return "website_changes"
        if news_score >= 3 and news_score > website_score:
            return "news"
        return "general"

    def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Route the query to the appropriate agent and return its response."""
        start_time = time.time()
        context = context or {}

        detected_intent = self._detect_query_intent(query)
        context["detected_intent"] = detected_intent

        if detected_intent == "website_changes":
            selected_agent = self.website_changes_agent
        elif detected_intent == "news":
            selected_agent = self.news_agent
        else:
            selected_agent = self.general_agent

        routing_time = time.time() - start_time
        result = selected_agent.execute(query, context)

        result["orchestration"] = {
            "detected_intent": detected_intent,
            "selected_agent": selected_agent.name,
            "routing_time": round(routing_time, 4),
            "total_time": round(time.time() - start_time, 3),
            "framework": "agno",
        }

        self.log_execution(query, result, time.time() - start_time)
        return result

    def log_execution(self, query: str, result: Dict[str, Any], execution_time: float):
        self.execution_history.append({
            "query": query,
            "success": "error" not in result,
            "execution_time": execution_time,
            "timestamp": time.time(),
            "agent_used": result.get("orchestration", {}).get("selected_agent", "unknown"),
        })
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def get_stats(self) -> Dict[str, Any]:
        if not self.execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "agent_distribution": {},
            }
        successful = sum(1 for ex in self.execution_history if ex["success"])
        total = len(self.execution_history)
        agent_counts: Dict[str, int] = {}
        for ex in self.execution_history:
            agent = ex.get("agent_used", "unknown")
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        return {
            "total_executions": total,
            "success_rate": round(successful / total * 100, 2),
            "avg_execution_time": round(
                sum(ex["execution_time"] for ex in self.execution_history) / total, 3
            ),
            "agent_distribution": agent_counts,
            "framework": "agno",
        }
