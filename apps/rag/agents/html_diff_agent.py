"""
HTML Difference Agent - Handles queries about website changes using Agno framework.
"""
import time
import re
from typing import Dict, Any, List
from datetime import datetime, timedelta
from django.utils import timezone
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from apps.monitoring.models import HTMLDifference, Competitor
from django.contrib.auth.models import User


class HTMLDiffAgent:
    """
    Agno-based agent that handles queries about HTML differences and website changes.
    Queries the HTMLDifference model and formats responses about changes.
    """
    
    def __init__(self, api_key: str = None):
        """Initialize Agno agent with HTML diff tools."""
        self.name = "HTMLDiffFinder"
        self.execution_history = []
        
        # Create Agno agent with instructions (using OpenAI GPT-4o-mini)
        self.agent = Agent(
            name="HTML Difference Finder Agent",
            model=OpenAIChat(id="gpt-4o-mini", api_key=api_key),
            instructions=[
                "You are a specialist in tracking and reporting website changes.",
                "Help users understand what changes occurred on competitor websites.",
                "Provide clear summaries of HTML differences and content modifications.",
                "Focus on significant changes like pricing updates, feature additions, and content modifications.",
            ],
            markdown=True,
        )
    
    def can_handle(self, query: str, context: Dict[str, Any] = None) -> bool:
        """
        This agent handles queries about HTML differences and website changes.
        """
        context = context or {}
        detected_intent = context.get('detected_intent', 'general')
        return detected_intent == 'html_diff'
    
    def _extract_competitor_name(self, query: str) -> str:
        """Extract competitor name from query."""
        query_lower = query.lower()
        
        # Common competitor names
        competitors = ['honda', 'suzuki', 'kia', 'toyota', 'nissan']
        
        for comp in competitors:
            if comp in query_lower:
                return comp
        
        return None
    
    def _extract_time_range(self, query: str) -> Dict[str, Any]:
        """
        Extract time range from query (e.g., 'last week', 'last 2 changes').
        """
        query_lower = query.lower()
        
        # Default: last 7 days
        time_filter = {
            'days': 7,
            'limit': None
        }
        
        # Check for 'last N changes' pattern
        last_n_match = re.search(r'last\s+(\d+)\s+(change|update|modification)', query_lower)
        if last_n_match:
            time_filter['limit'] = int(last_n_match.group(1))
            time_filter['days'] = 365  # Get from last year, but limit results
        
        # Check for time-based patterns
        time_patterns = {
            r'last\s+week|past\s+week': 7,
            r'last\s+month|past\s+month': 30,
            r'last\s+(\d+)\s+days?': None,  # Will extract number
            r'yesterday': 1,
            r'today': 0,
        }
        
        for pattern, days in time_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if days is None:
                    # Extract the number
                    days = int(match.group(1))
                time_filter['days'] = days
                break
        
        return time_filter
    
    def _get_html_differences(
        self, 
        user: User, 
        competitor_name: str = None, 
        time_filter: Dict[str, Any] = None
    ) -> List[HTMLDifference]:
        """
        Retrieve HTML differences from database based on filters.
        """
        # Start with user's competitors
        queryset = HTMLDifference.objects.filter(
            competitor__user=user,
            competitor__is_deleted=False
        )
        
        # Filter by competitor if specified
        if competitor_name:
            queryset = queryset.filter(
                competitor__name__icontains=competitor_name
            )
        
        # Filter by time range
        if time_filter and time_filter.get('days') is not None:
            days = time_filter['days']
            if days >= 0:
                time_threshold = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(detected_at__gte=time_threshold)
        
        # Order by most recent
        queryset = queryset.order_by('-detected_at')
        
        # Limit results if specified
        if time_filter and time_filter.get('limit'):
            queryset = queryset[:time_filter['limit']]
        else:
            # Default limit to prevent huge responses
            queryset = queryset[:20]
        
        return list(queryset)
    
    def _format_difference(self, diff: HTMLDifference) -> Dict[str, Any]:
        """Format a single HTML difference for response."""
        return {
            'id': diff.id,
            'competitor': diff.competitor.name,
            'url': diff.url,
            'change_type': diff.change_type,
            'detected_at': diff.detected_at.isoformat(),
            'is_significant': diff.is_significant,
            'summary': diff.diff_summary,
            'details': diff.detailed_diff[:5] if diff.detailed_diff else []  # Limit details
        }
    
    def _generate_summary_text(self, differences: List[HTMLDifference], query: str) -> str:
        """
        Generate a natural language summary of the differences.
        """
        if not differences:
            return "No recent changes were found matching your query."
        
        # Group by competitor
        by_competitor = {}
        for diff in differences:
            comp_name = diff.competitor.name
            if comp_name not in by_competitor:
                by_competitor[comp_name] = []
            by_competitor[comp_name].append(diff)
        
        summary_parts = []
        
        for comp_name, diffs in by_competitor.items():
            summary_parts.append(f"\n**{comp_name}** ({len(diffs)} change{'s' if len(diffs) != 1 else ''}):")
            
            for idx, diff in enumerate(diffs[:10], 1):  # Limit to 10 per competitor
                time_ago = self._time_ago(diff.detected_at)
                change_desc = self._describe_change(diff)
                summary_parts.append(f"  {idx}. {change_desc} ({time_ago})")
        
        return "\n".join(summary_parts)
    
    def _time_ago(self, dt: datetime) -> str:
        """Convert datetime to human-readable 'time ago' format."""
        now = timezone.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "just now"
    
    def _describe_change(self, diff: HTMLDifference) -> str:
        """Create a human-readable description of the change."""
        summary = diff.diff_summary
        
        if diff.change_type == 'added':
            return f"New page added: {diff.url}"
        elif diff.change_type == 'removed':
            return f"Page removed: {diff.url}"
        else:  # modified
            if isinstance(summary, dict):
                total = summary.get('total_changes', 0)
                added = len(summary.get('added_sections', []))
                modified = len(summary.get('modified_sections', []))
                removed = len(summary.get('removed_sections', []))
                
                parts = []
                if added > 0:
                    parts.append(f"{added} section{'s' if added != 1 else ''} added")
                if modified > 0:
                    parts.append(f"{modified} section{'s' if modified != 1 else ''} modified")
                if removed > 0:
                    parts.append(f"{removed} section{'s' if removed != 1 else ''} removed")
                
                change_text = ", ".join(parts) if parts else f"{total} change{'s' if total != 1 else ''}"
                return f"{diff.url}: {change_text}"
            else:
                return f"Modified: {diff.url}"
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute HTML difference query.
        """
        start_time = time.time()
        context = context or {}
        
        # Get user from context (should be passed from view)
        user = context.get('user')
        if not user:
            return {
                'error': 'User context required for HTML diff queries',
                'agent': self.name
            }
        
        try:
            # Extract competitor name and time range from query
            competitor_name = self._extract_competitor_name(query)
            time_filter = self._extract_time_range(query)
            
            # Get HTML differences
            differences = self._get_html_differences(
                user=user,
                competitor_name=competitor_name,
                time_filter=time_filter
            )
            
            # Format response
            result = {
                'query': query,
                'answer': self._generate_summary_text(differences, query),
                'total_changes_found': len(differences),
                'changes': [self._format_difference(diff) for diff in differences],
                'filters_applied': {
                    'competitor': competitor_name or 'all',
                    'time_range_days': time_filter.get('days'),
                    'limit': time_filter.get('limit') or 20
                },
                'agent': {
                    'name': self.name,
                    'type': 'html_diff_finder',
                    'framework': 'agno',
                    'execution_time': round(time.time() - start_time, 3)
                }
            }
            
            # Log execution
            self.log_execution(query, result, time.time() - start_time)
            
            return result
            
        except Exception as e:
            error_result = {
                'error': f'HTML diff query failed: {str(e)}',
                'query': query,
                'agent': {
                    'name': self.name,
                    'framework': 'agno'
                }
            }
            self.log_execution(query, error_result, time.time() - start_time)
            return error_result
    
    def log_execution(self, query: str, result: Dict[str, Any], execution_time: float):
        """Log execution for statistics."""
        self.execution_history.append({
            'query': query,
            'success': 'error' not in result,
            'execution_time': execution_time,
            'timestamp': time.time()
        })
        
        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent execution statistics."""
        if not self.execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_execution_time': 0.0
            }
        
        successful = sum(1 for ex in self.execution_history if ex['success'])
        total = len(self.execution_history)
        avg_time = sum(ex['execution_time'] for ex in self.execution_history) / total
        
        return {
            'total_executions': total,
            'success_rate': round(successful / total * 100, 2),
            'avg_execution_time': round(avg_time, 3)
        }
