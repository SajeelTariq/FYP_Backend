from django.contrib import admin
from .models import VectorDocument, QueryLog


@admin.register(VectorDocument)
class VectorDocumentAdmin(admin.ModelAdmin):
    list_display = ['vector_id', 'competitor_metadata', 'embedding_model', 'chunk_index', 'created_at']
    list_filter = ['embedding_model', 'created_at']
    search_fields = ['vector_id', 'competitor_metadata__competitor__name']


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ['query_text', 'results_count', 'response_time', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query_text']
