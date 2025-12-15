"""
Orchestrator Agent - Routes queries to appropriate specialized agents.
"""
import re
from typing import Dict, Any, List
import time

from .base_agent import BaseAgent


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator agent that analyzes queries and routes them to specialized agents.
    Uses keyword matching and pattern recognition to determine query intent.
    """
    
    def __init__(self, agents: List[BaseAgent] = None):
        super().__init__("Orchestrator")
        self.agents = agents or []
        
        # Keywords that indicate HTML difference queries
        self.html_diff_keywords = [
            'change', 'changes', 'changed', 'modification', 'modifications', 'modified',
            'update', 'updates', 'updated', 'difference', 'differences', 'diff',
            'what was', 'what were', 'what happened', 'recent', 'recently',
            'last', 'latest', 'new', 'added', 'removed', 'altered',
            'website change', 'page change', 'content change',
            'before', 'after', 'compared to', 'vs', 'versus'
        ]
        
        # Temporal keywords that often appear in diff queries
        self.temporal_keywords = [
            'last week', 'last month', 'yesterday', 'today',
            'past week', 'past month', 'recent days', 'recently',
            'in the last', 'within', 'since'
        ]
    
    def register_agent(self, agent: BaseAgent):
        """Register a new specialized agent."""
        self.agents.append(agent)
    
    def can_handle(self, query: str, context: Dict[str, Any] = None) -> bool:
        """Orchestrator can handle all queries."""
        return True
    
    def _detect_query_intent(self, query: str) -> str:
        """
        Detect the intent of the query using keyword matching.
        
        Returns:
            'html_diff' or 'general'
        """
        query_lower = query.lower()
        
        # Check for HTML diff keywords
        html_diff_score = 0
        
        # Check for exact keyword matches
        for keyword in self.html_diff_keywords:
            if keyword in query_lower:
                html_diff_score += 2
        
        # Check for temporal keywords (strong indicator of diff queries)
        for keyword in self.temporal_keywords:
            if keyword in query_lower:
                html_diff_score += 3
        
        # Pattern matching for common diff query structures
        diff_patterns = [
            r'what.*(change|update|modification|difference)',
            r'(list|show|tell|get).*(change|update|modification)',
            r'(recent|latest|last|new).*(change|update|modification)',
            r'what (was|were|is|are).*(different|new|changed)',
            r'how.*(changed|updated|modified)',
        ]
        
        for pattern in diff_patterns:
            if re.search(pattern, query_lower):
                html_diff_score += 3
        
        # If score is high enough, classify as HTML diff query
        if html_diff_score >= 3:
            return 'html_diff'
        
        return 'general'
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Route the query to the appropriate agent based on intent detection.
        """
        start_time = time.time()
        context = context or {}
        
        # Detect query intent
        intent = self._detect_query_intent(query)
        
        # Find the appropriate agent
        selected_agent = None
        for agent in self.agents:
            # Add intent to context for agent decision
            agent_context = {**context, 'detected_intent': intent}
            if agent.can_handle(query, agent_context):
                selected_agent = agent
                break
        
        if not selected_agent:
            # Fallback to first agent (usually GeneralQueryAgent)
            selected_agent = self.agents[0] if self.agents else None
            if not selected_agent:
                return {
                    'error': 'No agents available to handle the query',
                    'query': query,
                    'orchestrator': self.name
                }
        
        # Execute the selected agent
        try:
            result = selected_agent.execute(query, context)
            
            # Add orchestration metadata
            result['orchestration'] = {
                'orchestrator': self.name,
                'selected_agent': selected_agent.name,
                'detected_intent': intent,
                'routing_time': round(time.time() - start_time, 3)
            }
            
            # Log execution
            self.log_execution(query, result, time.time() - start_time)
            
            return result
            
        except Exception as e:
            error_result = {
                'error': f'Agent execution failed: {str(e)}',
                'query': query,
                'selected_agent': selected_agent.name,
                'detected_intent': intent
            }
            self.log_execution(query, error_result, time.time() - start_time)
            return error_result
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about query routing."""
        if not self.execution_history:
            return {
                'total_queries': 0,
                'routing_distribution': {}
            }
        
        routing_dist = {}
        for ex in self.execution_history:
            # This would need to track which agent was selected
            # For now, return basic stats
            pass
        
        return {
            'total_queries': len(self.execution_history),
            'orchestrator_stats': self.get_stats()
        }
