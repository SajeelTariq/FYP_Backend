from django.db import models
from apps.monitoring.models import Competitor, CompetitorMetadata


class VectorDocument(models.Model):
    """Model to track documents stored in Milvus vector database."""
    competitor_metadata = models.ForeignKey(
        CompetitorMetadata, 
        on_delete=models.CASCADE, 
        related_name='vector_documents'
    )
    vector_id = models.CharField(max_length=255, unique=True, help_text="ID in Milvus")
    embedding_model = models.CharField(max_length=100, default='sentence-transformers')
    chunk_index = models.IntegerField(default=0, help_text="Chunk number for large documents")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vector Document'
        verbose_name_plural = 'Vector Documents'
        indexes = [
            models.Index(fields=['vector_id']),
        ]

    def __str__(self):
        return f"Vector {self.vector_id} - {self.competitor_metadata.competitor.name}"


class QueryLog(models.Model):
    """Log of RAG queries for analytics."""
    query_text = models.TextField()
    results_count = models.IntegerField(default=0)
    top_competitors = models.JSONField(default=list, help_text="List of competitor IDs in results")
    response_time = models.FloatField(help_text="Response time in seconds")
    similarity_threshold = models.FloatField(default=0.7)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Query Log'
        verbose_name_plural = 'Query Logs'

    def __str__(self):
        return f"Query: {self.query_text[:50]}... ({self.created_at})"
