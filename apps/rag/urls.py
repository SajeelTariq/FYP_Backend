from django.urls import path
from .views_chromadb import (
    rag_query,
    semantic_search,
    rag_stats,
    get_competitors
)

urlpatterns = [
    # ChromaDB RAG endpoints with hybrid retrieval
    path('query/', rag_query, name='rag-query'),
    path('search/', semantic_search, name='semantic-search'),
    path('stats/', rag_stats, name='rag-stats'),
    path('competitors/', get_competitors, name='get-competitors'),
]
