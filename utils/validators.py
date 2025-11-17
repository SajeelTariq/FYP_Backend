"""
Common validator functions.
"""
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import re


def validate_url(url):
    """
    Validate URL format.
    
    Args:
        url: URL string to validate
    
    Returns:
        bool: True if valid, raises ValidationError otherwise
    """
    validator = URLValidator()
    try:
        validator(url)
        return True
    except ValidationError:
        raise ValidationError(f"Invalid URL: {url}")


def validate_css_selector(selector):
    """
    Basic validation for CSS selectors.
    
    Args:
        selector: CSS selector string
    
    Returns:
        bool: True if valid
    """
    if not selector or not isinstance(selector, str):
        raise ValidationError("CSS selector must be a non-empty string")
    
    # Basic check for valid characters
    if not re.match(r'^[\w\s\.\#\[\]\=\:\-\>\+\~\*\"\',\(\)]+$', selector):
        raise ValidationError("Invalid CSS selector format")
    
    return True


def validate_json_structure(data, required_keys):
    """
    Validate JSON data has required keys.
    
    Args:
        data: Dictionary to validate
        required_keys: List of required key names
    
    Returns:
        bool: True if valid, raises ValidationError otherwise
    """
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary")
    
    missing_keys = [key for key in required_keys if key not in data]
    
    if missing_keys:
        raise ValidationError(f"Missing required keys: {', '.join(missing_keys)}")
    
    return True


def validate_date_range(start_date, end_date):
    """
    Validate that end_date is after start_date.
    
    Args:
        start_date: Start date
        end_date: End date
    
    Returns:
        bool: True if valid
    """
    if start_date >= end_date:
        raise ValidationError("End date must be after start date")
    
    return True
