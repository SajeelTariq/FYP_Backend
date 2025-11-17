"""
Helper functions for common operations.
"""
from datetime import datetime, timedelta
from django.utils import timezone
import hashlib
import random
import string


def generate_unique_id(prefix="", length=10):
    """
    Generate a unique ID string.
    
    Args:
        prefix: Optional prefix for the ID
        length: Length of random string
    
    Returns:
        Unique ID string
    """
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    return f"{prefix}{timestamp}_{random_string}" if prefix else f"{timestamp}_{random_string}"


def generate_hash(text):
    """
    Generate MD5 hash of text.
    
    Args:
        text: Text to hash
    
    Returns:
        Hash string
    """
    return hashlib.md5(text.encode()).hexdigest()


def get_date_range(days=7):
    """
    Get date range for last N days.
    
    Args:
        days: Number of days to go back
    
    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    return start_date, end_date


def truncate_text(text, max_length=100, suffix="..."):
    """
    Truncate text to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def safe_divide(numerator, denominator, default=0):
    """
    Safely divide two numbers, returning default if denominator is 0.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
    
    Returns:
        Division result or default
    """
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def format_currency(amount, currency="USD"):
    """
    Format number as currency.
    
    Args:
        amount: Numeric amount
        currency: Currency code
    
    Returns:
        Formatted currency string
    """
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥'
    }
    
    symbol = currency_symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def chunks(lst, n):
    """
    Split list into chunks of size n.
    
    Args:
        lst: List to split
        n: Chunk size
    
    Yields:
        Chunks of the list
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
