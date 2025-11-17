"""
RAG API Views for querying the knowledge base.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Avg

from .rag_service import RAGService
from .rag_models import RAGQuery, DocumentChunk
from .models import VectorDocument, QueryLog
from .serializers import (
    VectorDocumentSerializer, 
    QueryLogSerializer,
    QueryRequestSerializer
)


class VectorDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing vector documents."""
    queryset = VectorDocument.objects.all()
    serializer_class = VectorDocumentSerializer


class QueryLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing query logs."""
    queryset = QueryLog.objects.all()
    serializer_class = QueryLogSerializer


# New RAG Query Views

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_query(request):
    """
    RAG Query Endpoint - Complete RAG pipeline with retrieval + generation
    """
    query_text = request.data.get('query')
    
    if not query_text:
        return Response(
            {'error': 'Query text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    top_k = request.data.get('top_k', 5)
    competitor_filter = request.data.get('competitor_filter')
    
    if not isinstance(top_k, int) or top_k < 1 or top_k > 20:
        return Response(
            {'error': 'top_k must be an integer between 1 and 20'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        rag_service = RAGService()
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
    Semantic Search Endpoint - Retrieval only, no generation
    """
    query_text = request.data.get('query')
    
    if not query_text:
        return Response(
            {'error': 'Query text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    top_k = request.data.get('top_k', 10)
    competitor_filter = request.data.get('competitor_filter')
    
    try:
        rag_service = RAGService()
        results, retrieval_time = rag_service.semantic_search(
            query=query_text,
            top_k=top_k,
            competitor_filter=competitor_filter
        )
        
        return Response({
            'query': query_text,
            'results': results,
            'retrieval_time': round(retrieval_time, 3),
            'total_results': len(results)
        }, status=status.HTTP_200_OK)
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
    """
    try:
        total_chunks = DocumentChunk.objects.count()
        chunks_by_competitor = dict(
            DocumentChunk.objects.values('competitor_name')
            .annotate(count=Count('id'))
            .values_list('competitor_name', 'count')
        )
        
        query_stats = RAGQuery.objects.aggregate(
            total_queries=Count('id'),
            avg_retrieval_time=Avg('retrieval_time'),
            avg_generation_time=Avg('generation_time'),
            avg_total_time=Avg('total_time')
        )
        
        return Response({
            'total_chunks': total_chunks,
            'chunks_by_competitor': chunks_by_competitor,
            'total_queries': query_stats['total_queries'] or 0,
            'avg_retrieval_time': round(query_stats['avg_retrieval_time'] or 0, 3),
            'avg_generation_time': round(query_stats['avg_generation_time'] or 0, 3),
            'avg_total_time': round(query_stats['avg_total_time'] or 0, 3)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error fetching statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def query_history(request):
    """
    Get recent RAG queries
    """
    try:
        limit = int(request.GET.get('limit', 10))
        limit = min(limit, 50)
        
        queries = RAGQuery.objects.all()[:limit]
        
        result = {
            'queries': [
                {
                    'id': q.id,
                    'query': q.query_text,
                    'answer': q.generated_answer,
                    'created_at': q.created_at.isoformat(),
                    'metrics': {
                        'retrieval_time': q.retrieval_time,
                        'generation_time': q.generation_time,
                        'total_time': q.total_time,
                        'chunks_retrieved': q.top_k
                    }
                }
                for q in queries
            ]
        }
        
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error fetching history: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_competitors(request):
    """
    Get list of available competitors for dropdown filter
    
    Response:
    {
        "competitors": [
            {"name": "Honda", "count": 450},
            {"name": "Suzuki", "count": 400},
            {"name": "Kia", "count": 384}
        ]
    }
    """
    try:
        competitors = DocumentChunk.objects.values('competitor_name').annotate(
            count=Count('id')
        ).order_by('competitor_name')
        
        result = {
            'competitors': [
                {
                    'name': comp['competitor_name'],
                    'count': comp['count']
                }
                for comp in competitors
            ]
        }
        
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Error fetching competitors: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Keep the old class-based view for backward compatibility
class RAGQueryView(viewsets.ViewSet):
    """Legacy API endpoint for RAG queries."""
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        """
        Perform a RAG query against the vector database.
        """
        serializer = QueryRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Use new RAG service
        try:
            rag_service = RAGService()
            result = rag_service.query(
                query_text=serializer.validated_data['query'],
                top_k=serializer.validated_data.get('top_k', 5)
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            results = {
                'query': serializer.validated_data['query'],
                'results': [],
            'message': 'RAG query logic to be implemented'
        }
        
        return Response(results, status=status.HTTP_200_OK)
