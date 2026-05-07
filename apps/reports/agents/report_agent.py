"""
Report Generator Agent — builds executive and analyst reports from DB data.
"""
import json
import time
import logging
from datetime import date
from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from django.contrib.auth.models import User
from django.conf import settings

from apps.monitoring.models import Competitor, HTMLDifference
from apps.social_media.models import SocialMediaPost, JobPosting

logger = logging.getLogger(__name__)

# Truncate post content so we don't blow up the context window
_POST_CONTENT_LIMIT = 400


class ReportAgent:
    def __init__(self, api_key: str = None):
        self.name = "ReportGenerator"
        self.agent = Agent(
            name="Report Generator Agent",
            model=OpenAIChat(
                id="gpt-4o-mini",
                api_key=api_key or settings.OPENAI_API_KEY,
            ),
            instructions=[
                "You are a senior business intelligence analyst.",
                "You write clear, insightful competitive intelligence reports.",
                "Always respond with valid JSON only — no markdown, no extra text.",
            ],
            markdown=False,
        )

    # ------------------------------------------------------------------
    # Data fetching helpers
    # ------------------------------------------------------------------

    def _get_website_changes(self, competitor: Competitor, start: date, end: date) -> list:
        diffs = (
            HTMLDifference.objects
            .filter(
                competitor=competitor,
                detected_at__date__gte=start,
                detected_at__date__lte=end,
            )
            .order_by('-detected_at')
            .select_related('competitor')
        )
        result = []
        for d in diffs:
            result.append({
                "url": d.url,
                "change_type": d.change_type,
                "detected_at": d.detected_at.strftime("%Y-%m-%d %H:%M"),
                "is_significant": d.is_significant,
                "llm_summary": d.llm_summary or "",
                "added_sections": d.diff_summary.get("added_sections", []) if isinstance(d.diff_summary, dict) else [],
                "removed_sections": d.diff_summary.get("removed_sections", []) if isinstance(d.diff_summary, dict) else [],
                "modified_sections": d.diff_summary.get("modified_sections", []) if isinstance(d.diff_summary, dict) else [],
            })
        return result

    def _get_social_posts(self, competitor: Competitor, start: date, end: date) -> list:
        posts = (
            SocialMediaPost.objects
            .filter(
                competitor=competitor,
                posted_at__date__gte=start,
                posted_at__date__lte=end,
            )
            .order_by('-posted_at')
        )
        result = []
        for p in posts:
            result.append({
                "platform": p.platform,
                "content": (p.content or "")[:_POST_CONTENT_LIMIT],
                "post_type": p.post_type,
                "posted_at": p.posted_at.strftime("%Y-%m-%d") if p.posted_at else "",
                "likes": p.num_likes,
                "comments": p.num_comments,
                "shares": p.num_shares,
            })
        return result

    def _get_job_postings(self, competitor: Competitor, start: date, end: date) -> list:
        jobs = (
            JobPosting.objects
            .filter(
                competitor=competitor,
                first_seen_at__date__gte=start,
                first_seen_at__date__lte=end,
            )
            .order_by('-first_seen_at')
        )
        result = []
        for j in jobs:
            result.append({
                "title": j.title,
                "location": j.location,
                "employment_type": j.employment_type,
                "seniority_level": j.seniority_level,
                "job_function": j.job_function,
                "posted_at": j.posted_at.strftime("%Y-%m-%d") if j.posted_at else "",
                "is_new": j.is_new,
            })
        return result

    def _build_competitor_context(self, competitor: Competitor, start: date, end: date) -> dict:
        return {
            "id": competitor.id,
            "name": competitor.name,
            "website": competitor.website_base_url or "",
            "website_changes": self._get_website_changes(competitor, start, end),
            "social_posts": self._get_social_posts(competitor, start, end),
            "job_postings": self._get_job_postings(competitor, start, end),
        }

    # ------------------------------------------------------------------
    # LLM calls
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        response = self.agent.run(prompt)
        return response.content or ""

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        # Strip markdown code fences if model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def _generate_executive(self, competitors_data: list, period: dict) -> dict:
        prompt = f"""
You are writing an EXECUTIVE SUMMARY competitive intelligence report.
Period: {period['start']} to {period['end']}

Rules:
- Executive summary: 3-4 sentences covering the overall competitive landscape across ALL competitors.
- Per competitor: a single concise paragraph (4-6 sentences) that covers website changes, social media activity, AND job postings together — giving a complete picture in brief.
- Focus on business impact: pricing moves, product launches, hiring signals, strategic messaging.
- Do NOT use bullet points. Write in professional business prose.

Competitor data:
{json.dumps(competitors_data, indent=2)}

Respond ONLY with this JSON (no extra text):
{{
  "executive_summary": "<overall landscape paragraph>",
  "competitors": [
    {{
      "id": <int>,
      "name": "<name>",
      "summary": "<complete competitor summary paragraph>"
    }}
  ]
}}
"""
        raw = self._call_llm(prompt)
        result = self._parse_json(raw)

        # Attach counts so PDF generator can display stats bar
        comp_map = {c["id"]: c for c in competitors_data}
        for comp in result.get("competitors", []):
            raw_comp = comp_map.get(comp["id"], {})
            comp["raw_data"] = {
                "website_changes_count": len(raw_comp.get("website_changes", [])),
                "social_posts_count": len(raw_comp.get("social_posts", [])),
                "new_job_postings_count": len(raw_comp.get("job_postings", [])),
            }

        return result

    def _generate_analyst(self, competitors_data: list, period: dict) -> dict:
        prompt = f"""
You are writing a detailed ANALYST competitive intelligence report.
Period: {period['start']} to {period['end']}

Rules:
- Executive summary: 4-5 sentences covering the overall competitive landscape.
- Per competitor provide:
  - "summary": 3-4 sentence overview of all activity.
  - "website_analysis": what changed on their website, what it signals strategically.
  - "social_analysis": themes and tone of social posts, what they are emphasizing.
  - "hiring_analysis": what the job postings reveal about their strategic direction.
  - "key_signals": list of 3-5 bullet-point strategic takeaways.
- Be specific — reference actual data (pages changed, post topics, job titles).
- If a section has no data, write "No activity in this period."

Competitor data:
{json.dumps(competitors_data, indent=2)}

Respond ONLY with this JSON (no extra text):
{{
  "executive_summary": "<overall summary>",
  "competitors": [
    {{
      "id": <int>,
      "name": "<name>",
      "summary": "<overview paragraph>",
      "website_analysis": "<website changes analysis>",
      "social_analysis": "<social media analysis>",
      "hiring_analysis": "<job postings analysis>",
      "key_signals": ["<signal 1>", "<signal 2>", "<signal 3>"],
      "raw_data": {{
        "website_changes_count": <int>,
        "social_posts_count": <int>,
        "new_job_postings_count": <int>
      }}
    }}
  ]
}}
"""
        raw = self._call_llm(prompt)
        result = self._parse_json(raw)

        # Attach raw data back for analyst (so frontend can render actual lists)
        comp_map = {c["id"]: c for c in competitors_data}
        for comp in result.get("competitors", []):
            raw_comp = comp_map.get(comp["id"], {})
            comp["website_changes"] = raw_comp.get("website_changes", [])
            comp["social_posts"] = raw_comp.get("social_posts", [])
            comp["job_postings"] = raw_comp.get("job_postings", [])

        return result

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def execute(
        self,
        user: User,
        report_type: str,
        period_start: date,
        period_end: date,
        competitor_ids: list = None,
    ) -> dict:
        start_time = time.time()

        competitors = Competitor.objects.filter(user=user, is_deleted=False)
        if competitor_ids:
            competitors = competitors.filter(id__in=competitor_ids)

        if not competitors.exists():
            return {"error": "No competitors found for this user."}

        period = {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        }

        try:
            competitors_data = [
                self._build_competitor_context(c, period_start, period_end)
                for c in competitors
            ]

            if report_type == "executive":
                content = self._generate_executive(competitors_data, period)
            else:
                content = self._generate_analyst(competitors_data, period)

            content["report_type"] = report_type
            content["period"] = period
            content["generated_in_seconds"] = round(time.time() - start_time, 2)

            return content

        except Exception as e:
            logger.exception("ReportAgent failed")
            return {"error": str(e)}
