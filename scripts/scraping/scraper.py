"""
Web scraping utilities.

Place your web scraping scripts here.
Example functions:
- scrape_website(url, selectors)
- extract_product_data(html)
- handle_pagination(driver, url)
"""

import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def scrape_webpage(url, headers=None):
    """
    Basic webpage scraper.
    
    Args:
        url: URL to scrape
        headers: Optional HTTP headers
    
    Returns:
        BeautifulSoup object or None
    """
    try:
        response = requests.get(url, headers=headers or {}, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return None


def extract_data_with_selectors(soup, selectors):
    """
    Extract data using CSS selectors.
    
    Args:
        soup: BeautifulSoup object
        selectors: Dictionary of {field_name: css_selector}
    
    Returns:
        Dictionary of extracted data
    """
    data = {}
    for field, selector in selectors.items():
        try:
            element = soup.select_one(selector)
            data[field] = element.text.strip() if element else None
        except Exception as e:
            logger.error(f"Error extracting {field}: {str(e)}")
            data[field] = None
    
    return data


# Add your existing scraping functions here
