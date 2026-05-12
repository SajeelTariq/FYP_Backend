"""
Custom decorators for views and functions.
"""
from functools import wraps
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def cache_response(timeout=300):
    """
    Cache decorator for view responses.
    
    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cached result for {cache_key}")
            
            return result
        return wrapper
    return decorator


def log_execution_time(func):
    """
    Decorator to log execution time of a function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        execution_time = time.time() - start_time
        logger.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
        
        return result
    return wrapper


def handle_exceptions(func):
    """
    Decorator to handle exceptions in API views.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return Response(
                {
                    "success": False,
                    "message": "An error occurred",
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper


def require_active_competitor(func):
    """
    Decorator to ensure competitor is active before processing.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get competitor from kwargs
        competitor = kwargs.get('competitor')
        
        if competitor and competitor.is_deleted:
            return Response(
                {
                    "success": False,
                    "message": "Competitor is not active"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return func(*args, **kwargs)
    return wrapper
