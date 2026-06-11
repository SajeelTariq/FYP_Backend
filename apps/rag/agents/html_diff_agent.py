"""
Website Changes Agent - handles queries about competitor website changes using Agno tool-calling.
"""
import json
import time
from datetime import timedelta
from typing import Dict, Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from django.utils import timezone


class WebsiteChangesAgent:
    """
    Agno agent that answers questions about competitor website changes.
    Defines a DB-search tool as a closure so the LLM decides the filter parameters.
    """

    def __init__(self, api_key: str = None):
        self.name = "WebsiteChanges"
        self.api_key = api_key
        self.execution_history = []

    def can_handle(self, query: str, context: Dict[str, Any] = None) -> bool:
        context = context or {}
        return context.get("detected_intent") == "website_changes"

    def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        start_time = time.time()
        context = context or {}

        user = context.get("user")
        if not user:
            return {"error": "User context required for website change queries", "agent": self.name}

        # --- Tool defined as closure so it captures the authenticated user ---
        def search_website_changes(
            competitor_name: str = None,
            days: int = 7,
            change_category: str = None,
            is_significant_only: bool = False,
            limit: int = 20,
        ) -> str:
            """
            Search competitor website changes stored in the database.

            Args:
                competitor_name: Name (or partial name) of the competitor to filter by.
                    Pass None to search across all competitors.
                days: How many days back to search (e.g. 7 for last week, 30 for last month).
                change_category: Filter by category — one of 'critical', 'non_critical',
                    or 'technical'. Pass None to return all categories.
                is_significant_only: If True, return only business-significant changes.
                limit: Maximum number of results to return (default 20, max 50).

            Returns:
                JSON string with a list of website change records.
            """
            from apps.monitoring.models import HTMLDifference

            qs = HTMLDifference.objects.filter(
                competitor__user=user,
                competitor__is_deleted=False,
                is_onboarding_snapshot=False,
            ).select_related("competitor")

            if competitor_name:
                qs = qs.filter(competitor__name__icontains=competitor_name)

            if days and days > 0:
                cutoff = timezone.now() - timedelta(days=days)
                qs = qs.filter(detected_at__gte=cutoff)

            if change_category and change_category in ("critical", "non_critical", "technical"):
                qs = qs.filter(change_category=change_category)

            if is_significant_only:
                qs = qs.filter(is_significant=True)

            qs = qs.order_by("-detected_at")[: min(int(limit), 50)]

            results = [
                {
                    "id": r.pk,
                    "competitor_name": r.competitor.name,
                    "url": r.url,
                    "change_type": r.change_type,
                    "change_category": r.change_category,
                    "is_significant": r.is_significant,
                    "detected_at": r.detected_at.isoformat(),
                    "llm_summary": r.llm_summary or "",
                }
                for r in qs
            ]

            if not results:
                return json.dumps({"found": 0, "changes": [], "message": "No website changes found matching your filters."})

            return json.dumps({"found": len(results), "changes": results})

        # --- Build agent with the user-scoped tool ---
        agent = Agent(
            name="Website Changes Agent",
            model=OpenAIChat(id="gpt-4o-mini", api_key=self.api_key),
            tools=[search_website_changes],
            instructions=[
                "You are a competitive intelligence assistant that helps users understand changes made to competitor websites.",
                "Always call the search_website_changes tool to fetch data before answering — never guess.",
                "When the user mentions a time range like 'last week', 'last month', or 'last N days', map it to the `days` parameter.",
                "When the user asks about 'critical' changes, pass change_category='critical'. "
                "For 'technical' changes pass change_category='technical'. "
                "For 'minor' or 'non-critical' changes pass change_category='non_critical'.",
                "When the user asks for 'significant' or 'important' changes, set is_significant_only=True.",
                "Summarise the results clearly: group by competitor if multiple competitors are present, "
                "mention the change type (added/removed/modified), the category, whether it was significant, "
                "and include the URL and date for each change.",
                "Use the llm_summary field from each record as the human-readable description of what changed.",
                "If no results are found, say so honestly and suggest the user try a broader time range or different filters.",
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
                    "type": "website_changes",
                    "framework": "agno",
                    "execution_time": round(time.time() - start_time, 3),
                },
            }
            self.log_execution(query, result, time.time() - start_time)
            return result

        except Exception as e:
            error_result = {
                "error": f"Website changes query failed: {str(e)}",
                "query": query,
                "agent": {"name": self.name, "type": "website_changes", "framework": "agno"},
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


# Keep the old class name as an alias so existing imports don't break
HTMLDiffAgent = WebsiteChangesAgent
