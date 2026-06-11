"""
News Agent - handles queries about competitor news articles using Agno tool-calling.
"""
import json
import time
from datetime import timedelta
from typing import Dict, Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from django.utils import timezone


class NewsAgent:
    """
    Agno agent that answers questions about competitor news coverage.
    Defines a DB-search tool as a closure so the LLM decides the filter parameters.
    """

    def __init__(self, api_key: str = None):
        self.name = "News"
        self.api_key = api_key
        self.execution_history = []

    def can_handle(self, query: str, context: Dict[str, Any] = None) -> bool:
        context = context or {}
        return context.get("detected_intent") == "news"

    def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        start_time = time.time()
        context = context or {}

        user = context.get("user")
        if not user:
            return {"error": "User context required for news queries", "agent": self.name}

        # --- Tool defined as closure so it captures the authenticated user ---
        def search_news(
            competitor_name: str = None,
            days: int = 7,
            search_keyword: str = None,
            limit: int = 20,
        ) -> str:
            """
            Search news articles about competitors stored in the database.

            Args:
                competitor_name: Name (or partial name) of the competitor to filter by.
                    Pass None to search across all competitors.
                days: How many days back to search (e.g. 7 for last week, 30 for last month).
                search_keyword: Keyword to search within article titles or source names.
                    Pass None to return all articles without keyword filtering.
                limit: Maximum number of articles to return (default 20, max 50).

            Returns:
                JSON string with a list of news article records.
            """
            from django.db.models import Min, Q
            from apps.monitoring.models import Competitor, NewsArticle

            competitor_ids = Competitor.objects.filter(
                user=user, is_deleted=False
            ).values_list("id", flat=True)

            cutoff = timezone.now() - timedelta(days=max(1, int(days)))

            # Deduplicate by URL (same as dashboard news_feed)
            unique_ids_qs = (
                NewsArticle.objects
                .filter(competitor_id__in=competitor_ids, published_at__gte=cutoff)
                .values("url")
                .annotate(min_id=Min("id"))
                .values_list("min_id", flat=True)
            )

            qs = (
                NewsArticle.objects
                .filter(id__in=unique_ids_qs)
                .select_related("competitor")
                .order_by("-published_at")
            )

            if competitor_name:
                qs = qs.filter(competitor__name__icontains=competitor_name)

            if search_keyword:
                qs = qs.filter(
                    Q(title__icontains=search_keyword) | Q(source__icontains=search_keyword)
                )

            qs = qs[: min(int(limit), 50)]

            results = [
                {
                    "title": a.title,
                    "source": a.source or "Unknown",
                    "url": a.url,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                    "competitor_name": a.competitor.name,
                }
                for a in qs
            ]

            if not results:
                return json.dumps({"found": 0, "articles": [], "message": "No news articles found matching your filters."})

            return json.dumps({"found": len(results), "articles": results})

        # --- Build agent with the user-scoped tool ---
        agent = Agent(
            name="News Agent",
            model=OpenAIChat(id="gpt-4o-mini", api_key=self.api_key),
            tools=[search_news],
            instructions=[
                "You are a competitive intelligence assistant that helps users stay informed about news coverage of their competitors.",
                "Always call the search_news tool to fetch data before answering — never guess or invent articles.",
                "When the user mentions a time range like 'last week', 'last month', or 'last N days', map it to the `days` parameter.",
                "When the user mentions a specific topic or keyword, pass it as `search_keyword`.",
                "Present results in a clear, readable format: group articles by competitor when multiple competitors appear, "
                "include the article title, source, publication date, and URL for each article.",
                "If asked for a summary, highlight the most notable or recent stories.",
                "If no results are found, say so honestly and suggest the user try a broader time range or different keywords.",
                "Keep the response concise and professional.",
            ],
            markdown=True,
        )

        try:
            response = agent.run(query)
            answer = response.content if hasattr(response, "content") else str(response)

            result = {
                "query": query,
                "answer": answer,
                "agent": {
                    "name": self.name,
                    "type": "news",
                    "framework": "agno",
                    "execution_time": round(time.time() - start_time, 3),
                },
            }
            self.log_execution(query, result, time.time() - start_time)
            return result

        except Exception as e:
            error_result = {
                "error": f"News query failed: {str(e)}",
                "query": query,
                "agent": {"name": self.name, "type": "news", "framework": "agno"},
            }
            self.log_execution(query, error_result, time.time() - start_time)
            return error_result

    def log_execution(self, query: str, result: Dict[str, Any], execution_time: float):
        self.execution_history.append({
            "query": query,
            "success": "error" not in result,
            "execution_time": execution_time,
            "timestamp": time.time(),
        })
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def get_stats(self) -> Dict[str, Any]:
        if not self.execution_history:
            return {"total_executions": 0, "success_rate": 0.0, "avg_execution_time": 0.0}
        successful = sum(1 for ex in self.execution_history if ex["success"])
        total = len(self.execution_history)
        return {
            "name": self.name,
            "total_executions": total,
            "success_rate": round(successful / total * 100, 2),
            "avg_execution_time": round(
                sum(ex["execution_time"] for ex in self.execution_history) / total, 3
            ),
        }
