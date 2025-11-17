from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VectorDocumentViewSet, 
    QueryLogViewSet, 
    RAGQueryView,
    rag_query,
    semantic_search,
    rag_stats,
    query_history,
    get_competitors
)

router = DefaultRouter()
router.register(r'documents', VectorDocumentViewSet)
router.register(r'logs', QueryLogViewSet)
router.register(r'legacy-query', RAGQueryView, basename='rag-legacy')

urlpatterns = [
    path('', include(router.urls)),
    
    # New RAG endpoints
    path('query/', rag_query, name='rag-query'),
    path('search/', semantic_search, name='semantic-search'),
    path('stats/', rag_stats, name='rag-stats'),
    path('history/', query_history, name='query-history'),
    path('competitors/', get_competitors, name='get-competitors'),
]
