"""
Orchestrator Agent - Routes queries to appropriate specialized agents using Agno framework.
"""
import time
import re
from typing import Dict, Any, List

from .general_query_agent import GeneralQueryAgent
from .html_diff_agent import HTMLDiffAgent


class OrchestratorAgent:
    """
    Agno-based orchestrator that routes queries to specialized agents.
    Determines intent using keyword matching and delegates to appropriate agent.
    """
    
    # Keywords that suggest HTML diff queries
    html_diff_keywords = [
        'change', 'changes', 'changed', 'modification', 'modifications', 'modified',
        'update', 'updates', 'updated', 'difference', 'differences', 'diff',
        'what was', 'what were', 'what happened', 'recent', 'recently',
        'last', 'latest', 'new', 'added', 'removed', 'altered',
        'website change', 'page change', 'content change',
        'before', 'after', 'compared to', 'vs', 'versus'
    ]
    
    # Temporal keywords that often appear in diff queries
    temporal_keywords = [
        'last week', 'last month', 'yesterday', 'today',
        'past week', 'past month', 'recent days', 'recently',
        'in the last', 'within', 'since', 'ago'
    ]
    
    def __init__(self, api_key: str = None):
        """Initialize orchestrator with specialized agents."""
        self.name = "Orchestrator"
        self.api_key = api_key
        self.execution_history = []
        
        # Initialize specialized agents (Agno-based)
        self.general_agent = GeneralQueryAgent(api_key=api_key)
        self.html_diff_agent = HTMLDiffAgent(api_key=api_key)
        
        self.agents = [self.general_agent, self.html_diff_agent]
    
    def _detect_query_intent(self, query: str) -> str:
        """
        Detect query intent using keyword matching and pattern recognition.
        
        Returns:
            'html_diff' or 'general'
        """
        query_lower = query.lower()
        score = 0
        
        # Check for HTML diff keywords
        for keyword in self.html_diff_keywords:
            if keyword in query_lower:
                score += 2
        
        # Check for temporal keywords (strong indicator of diff queries)
        for keyword in self.temporal_keywords:
            if keyword in query_lower:
                score += 3
        
        # Check for specific patterns
        diff_patterns = [
            r'what\s+(changed|updated|modified)',
            r'(changes|updates|modifications)\s+(in|on|to)',
            r'last\s+\d+\s+(change|update|modification)',
            r'(show|list|tell)\s+.*(change|update|modification)',
            r'(difference|diff)\s+(between|from)',
        ]
        
        for pattern in diff_patterns:
            if re.search(pattern, query_lower):
                score += 3
        
        # Threshold for HTML diff intent
        # Score >= 3 suggests HTML diff query
        if score >= 3:
            return 'html_diff'
        return 'general'
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Route query to appropriate agent based on detected intent.
        
        Args:
            query: User query
            context: Additional context (user, top_k, competitor_filter, etc.)
            
        Returns:
            Response from the selected agent with orchestration metadata
        """
        start_time = time.time()
        context = context or {}
        
        # Detect query intent
        detected_intent = self._detect_query_intent(query)
        
        # Add detected intent to context
        context['detected_intent'] = detected_intent
        
        # Route to appropriate agent
        if detected_intent == 'html_diff':
            selected_agent = self.html_diff_agent
        else:
            selected_agent = self.general_agent
        
        # Execute selected agent
        routing_time = time.time() - start_time
        result = selected_agent.execute(query, context)
        
        # Add orchestration metadata
        result['orchestration'] = {
            'detected_intent': detected_intent,
            'selected_agent': selected_agent.name,
            'routing_time': round(routing_time, 4),
            'total_time': round(time.time() - start_time, 3),
            'framework': 'agno'
        }
        
        # Log execution
        self.log_execution(query, result, time.time() - start_time)
        
        return result
    
    def log_execution(self, query: str, result: Dict[str, Any], execution_time: float):
        """Log execution for statistics."""
        self.execution_history.append({
            'query': query,
            'success': 'error' not in result,
            'execution_time': execution_time,
            'timestamp': time.time(),
            'agent_used': result.get('orchestration', {}).get('selected_agent', 'unknown')
        })
        
        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator execution statistics."""
        if not self.execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_execution_time': 0.0,
                'agent_distribution': {}
            }
        
        successful = sum(1 for ex in self.execution_history if ex['success'])
        total = len(self.execution_history)
        avg_time = sum(ex['execution_time'] for ex in self.execution_history) / total
        
        # Calculate agent distribution
        agent_counts = {}
        for ex in self.execution_history:
            agent = ex.get('agent_used', 'unknown')
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        return {
            'total_executions': total,
            'success_rate': round(successful / total * 100, 2),
            'avg_execution_time': round(avg_time, 3),
            'agent_distribution': agent_counts,
            'framework': 'agno'
        }
