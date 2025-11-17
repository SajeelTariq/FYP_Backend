"""
Response utilities for consistent API responses.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """
    Return a standardized success response.
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
    
    Returns:
        Response object
    """
    response_data = {
        "success": True,
        "message": message,
        "data": data
    }
    return Response(response_data, status=status_code)


def error_response(message="Error occurred", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Return a standardized error response.
    
    Args:
        message: Error message
        errors: Additional error details
        status_code: HTTP status code
    
    Returns:
        Response object
    """
    response_data = {
        "success": False,
        "message": message,
    }
    
    if errors:
        response_data["errors"] = errors
    
    return Response(response_data, status=status_code)


def paginated_response(queryset, serializer_class, request, message="Success"):
    """
    Return a paginated response.
    
    Args:
        queryset: Django queryset
        serializer_class: Serializer class to use
        request: Request object
        message: Success message
    
    Returns:
        Response object with pagination
    """
    from rest_framework.pagination import PageNumberPagination
    
    paginator = PageNumberPagination()
    paginated_queryset = paginator.paginate_queryset(queryset, request)
    serializer = serializer_class(paginated_queryset, many=True)
    
    return paginator.get_paginated_response({
        "success": True,
        "message": message,
        "data": serializer.data
    })
