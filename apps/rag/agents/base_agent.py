"""
Base Agent class for all RAG agents.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import time


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str):
        self.name = name
        self.execution_history = []
    
    @abstractmethod
    def can_handle(self, query: str, context: Dict[str, Any] = None) -> bool:
        """
        Determine if this agent can handle the given query.
        
        Args:
            query: The user's query string
            context: Additional context information
            
        Returns:
            Boolean indicating if this agent can handle the query
        """
        pass
    
    @abstractmethod
    def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the agent's main logic.
        
        Args:
            query: The user's query string
            context: Additional context information
            
        Returns:
            Dictionary containing the agent's response
        """
        pass
    
    def log_execution(self, query: str, result: Dict[str, Any], execution_time: float):
        """Log execution details for debugging and monitoring."""
        self.execution_history.append({
            'timestamp': time.time(),
            'query': query,
            'result_keys': list(result.keys()),
            'execution_time': execution_time,
            'success': 'error' not in result
        })
        
        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics for this agent."""
        if not self.execution_history:
            return {
                'agent_name': self.name,
                'total_executions': 0,
                'success_rate': 0,
                'avg_execution_time': 0
            }
        
        total = len(self.execution_history)
        successes = sum(1 for ex in self.execution_history if ex['success'])
        avg_time = sum(ex['execution_time'] for ex in self.execution_history) / total
        
        return {
            'agent_name': self.name,
            'total_executions': total,
            'success_rate': successes / total * 100,
            'avg_execution_time': round(avg_time, 3)
        }
