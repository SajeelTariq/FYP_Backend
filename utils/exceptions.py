"""
Custom exception classes for the application.
"""


class ScrapingError(Exception):
    """Exception raised for scraping-related errors."""
    pass


class EmbeddingError(Exception):
    """Exception raised for embedding generation errors."""
    pass


class MilvusConnectionError(Exception):
    """Exception raised for Milvus connection errors."""
    pass


class DataProcessingError(Exception):
    """Exception raised for data processing errors."""
    pass


class AnalyticsError(Exception):
    """Exception raised for analytics calculation errors."""
    pass
