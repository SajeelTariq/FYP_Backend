"""
RAG-specific models for document chunks and embeddings storage in PostgreSQL.
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
import numpy as np


class DocumentChunk(models.Model):
    """Store document chunks with embeddings in PostgreSQL."""
    
    # Source information
    source_file = models.CharField(max_length=500, help_text="Original JSON filename")
    competitor_name = models.CharField(max_length=100, db_index=True)
    url = models.URLField(max_length=1000)
    title = models.CharField(max_length=500, blank=True)
    
    # Content
    chunk_text = models.TextField(help_text="Text chunk for RAG retrieval")
    chunk_index = models.IntegerField(default=0, help_text="Position in document")
    chunk_size = models.IntegerField(help_text="Number of characters in chunk")
    
    # Embedding (384 dimensions for sentence-transformers/all-MiniLM-L6-v2)
    # Using ArrayField as fallback for systems without pgvector
    embedding = ArrayField(
        models.FloatField(),
        size=384,
        help_text="384-dimensional embedding vector"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['competitor_name', 'source_file', 'chunk_index']
        verbose_name = 'Document Chunk'
        verbose_name_plural = 'Document Chunks'
        indexes = [
            models.Index(fields=['competitor_name', 'created_at']),
            models.Index(fields=['source_file']),
        ]

    def __str__(self):
        return f"{self.competitor_name} - {self.source_file[:50]} (Chunk {self.chunk_index})"


class RAGQuery(models.Model):
    """Log RAG queries with retrieval metadata."""
    
    query_text = models.TextField()
    retrieved_chunks = models.JSONField(default=list, help_text="Retrieved chunk IDs and scores")
    generated_answer = models.TextField(blank=True)
    
    # Performance metrics
    retrieval_time = models.FloatField(help_text="Time to retrieve chunks (seconds)")
    generation_time = models.FloatField(help_text="Time to generate answer (seconds)")
    total_time = models.FloatField(help_text="Total response time (seconds)")
    
    # Query metadata
    top_k = models.IntegerField(default=5, help_text="Number of chunks retrieved")
    model_used = models.CharField(max_length=100, default="gpt-4o-mini")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'RAG Query'
        verbose_name_plural = 'RAG Queries'

    def __str__(self):
        return f"Query: {self.query_text[:60]}... ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
