"""
Data processing and transformation utilities.

Place your data processing scripts here.
Example functions:
- clean_text_data(text)
- normalize_prices(price_data)
- extract_features(data)
"""

import re
import logging

logger = logging.getLogger(__name__)


def clean_text(text):
    """
    Clean and normalize text data.
    
    Args:
        text: Raw text string
    
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters
    text = re.sub(r'[^\w\s\.,!?-]', '', text)
    
    return text.strip()


def parse_price(price_string):
    """
    Extract numeric price from string.
    
    Args:
        price_string: String containing price (e.g., "$19.99")
    
    Returns:
        Float price value or None
    """
    try:
        # Remove currency symbols and commas
        clean_price = re.sub(r'[^\d.]', '', price_string)
        return float(clean_price)
    except (ValueError, AttributeError):
        logger.error(f"Failed to parse price: {price_string}")
        return None


# Add your existing data processing functions here
