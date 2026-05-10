"""
General Query Agent - Handles standard RAG queries using Agno framework.
"""
import time
from typing import Dict, Any
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from ..rag_service_chromadb import RAGServiceChroma


class GeneralQueryAgent:
    """
    Agno-based agent that handles general queries about products, features, pricing.
    Uses the existing ChromaDB RAG service as a custom tool.
    """
    
    def __init__(self, api_key: str = None):
        """Initialize Agno agent with RAG tool."""
        self.rag_service = RAGServiceChroma()
        self.name = "GeneralQuery"
        self.execution_history = []
        
        # Create Agno agent with instructions (using OpenAI GPT-4o-mini)
        self.agent = Agent(
            name="General Query Agent",
            model=OpenAIChat(id="gpt-4o-mini", api_key=api_key),
            instructions=[
                "You are a helpful assistant specialized in answering questions about automotive products.",
                "Use the provided competitor information to answer user queries accurately.",
                "When asked about vehicles, features, or pricing, retrieve relevant documents first.",
                "Provide clear, concise answers based on the retrieved information.",
            ],
            markdown=True,
        )
    
    def can_handle(self, query: str, context: Dict[str, Any] = None) -> bool:
        """
        This agent handles queries that are NOT about HTML differences.
        """
        context = context or {}
        detected_intent = context.get('detected_intent', 'general')
        return detected_intent == 'general'
    
    def execute(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute general RAG query using ChromaDB service.
        """
        start_time = time.time()
        context = context or {}
        
        # Extract parameters from context
        top_k = context.get('top_k', 5)
        competitor_filter = context.get('competitor_filter', 'all')
        
        try:
            # Use existing RAG service directly
            # (Agno agent would be used for more complex reasoning/multi-step tasks)
            result = self.rag_service.query(
                query_text=query,
                top_k=top_k,
                competitor_filter=competitor_filter
            )
            
            # Add agent metadata
            result['agent'] = {
                'name': self.name,
                'type': 'general_query',
                'framework': 'agno',
                'execution_time': round(time.time() - start_time, 3)
            }
            
            # Log execution
            self.log_execution(query, result, time.time() - start_time)
            
            return result
            
        except Exception as e:
            error_result = {
                'error': f'General query failed: {str(e)}',
                'agent': {
                    'name': self.name,
                    'type': 'general_query',
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
