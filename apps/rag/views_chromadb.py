"""
RAG API Views for querying the knowledge base with ChromaDB.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .rag_service_chromadb import RAGServiceChroma


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_query(request):
    """
    RAG Query Endpoint - Complete RAG pipeline with hybrid retrieval + generation
    
    Request body:
    {
        "query": "What are the features of Honda BR-V?",
        "top_k": 5,  // optional, default 5
        "competitor_filter": "honda"  // optional: honda, suzuki, kia, or all
    }
    """
    query_text = request.data.get('query')
    
    if not query_text:
        return Response(
            {'error': 'Query text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    top_k = request.data.get('top_k', 5)
    competitor_filter = request.data.get('competitor_filter', 'all')
    
    if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
        return Response(
            {'error': 'top_k must be an integer between 1 and 20'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        rag_service = RAGServiceChroma()
        result = rag_service.query(
            query_text=query_text,
            top_k=top_k,
            competitor_filter=competitor_filter
        )
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error processing query: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def semantic_search(request):
    """
    Semantic Search Endpoint - Hybrid retrieval only, no answer generation
    
    Request body:
    {
        "query": "Honda BR-V price",
        "top_k": 10,  // optional, default 5
        "competitor_filter": "honda"  // optional
    }
    """
    query_text = request.data.get('query')
    
    if not query_text:
        return Response(
            {'error': 'Query text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    top_k = request.data.get('top_k', 10)
    competitor_filter = request.data.get('competitor_filter', 'all')
    
    try:
        rag_service = RAGServiceChroma()
        result = rag_service.semantic_search(
            query=query_text,
            top_k=top_k,
            competitor_filter=competitor_filter
        )
        
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error performing search: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rag_stats(request):
    """
    RAG System Statistics
    
    Returns total chunks, chunks per competitor, and system info
    """
    try:
        rag_service = RAGServiceChroma()
        stats = rag_service.get_stats()
        
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error fetching statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_competitors(request):
    """
    Get list of competitors for dropdown
    
    Returns list of competitors with their chunk counts
    """
    try:
        rag_service = RAGServiceChroma()
        competitors = rag_service.get_competitors()
        
        # Add 'All' option
        all_option = {
            'name': 'All Competitors',
            'value': 'all',
            'chunk_count': sum(c['chunk_count'] for c in competitors)
        }
        
        return Response({
            'competitors': [all_option] + competitors
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error fetching competitors: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
