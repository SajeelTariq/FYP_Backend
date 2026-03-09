"""
Common validator functions.
"""
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import re
import requests
import logging

logger = logging.getLogger(__name__)


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


def validate_url_exists(url):
    """
    Check if a URL's domain actually exists.
    Auto-prepends https:// if no scheme is provided.

    Only rejects if the domain cannot be resolved (DNS failure) or the
    URL format is invalid. Timeouts, 4xx, and 5xx responses are accepted
    because the site may block automated requests while still being a real
    competitor — Firecrawl will handle the actual scraping.

    Args:
        url: URL string to check

    Returns:
        tuple: (is_valid: bool, error_or_normalized_url: str)
               On success: (True, normalized_url)
               On failure: (False, error_message)
    """
    # Auto-prepend https:// if no scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Validate format
    validator = URLValidator()
    try:
        validator(url)
    except ValidationError:
        return False, f"Invalid URL format: {url}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        # Any response (including 4xx/5xx) means the domain exists
        return True, url
    except requests.exceptions.ConnectionError as e:
        err_str = str(e).lower()
        # Only reject on DNS failure — the domain genuinely doesn't exist
        if 'name or service not known' in err_str or 'nodename nor servname' in err_str \
                or 'getaddrinfo failed' in err_str or 'name resolution' in err_str \
                or 'no such host' in err_str:
            return False, f"Domain does not exist: {url}"
        # Any other connection error (firewall, bot-blocking, etc.) — accept it
        logger.warning(f"Connection issue for {url} (assuming site exists): {e}")
        return True, url
    except requests.exceptions.Timeout:
        # Site is slow or blocking automated requests — still a real site
        logger.warning(f"Timeout checking {url} (assuming site exists)")
        return True, url
    except requests.exceptions.RequestException as e:
        # Unknown error — be lenient and accept
        logger.warning(f"Could not verify {url} (assuming site exists): {e}")
        return True, url


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
