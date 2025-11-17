"""
Celery tasks for scraping operations.
Integrated logic from Links_extractor.py, Scrape_HTML.py, and json_of_html.py
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import re
import hashlib
import json

logger = logging.getLogger(__name__)


@shared_task
def extract_competitor_links(competitor_id):
    """
    Extract all subpage links from competitor's website using Firecrawl API.
    Based on Links_extractor.py logic.
    
    Args:
        competitor_id: ID of the Competitor
    """
    from apps.monitoring.models import Competitor, ExtractedLinks
    
    try:
        competitor = Competitor.objects.get(id=competitor_id, is_deleted=False)
        input_url = competitor.website_base_url
        
        # Automatically add https:// if not present
        if not input_url.startswith(("http://", "https://")):
            input_url = "https://" + input_url
        
        parsed_url = urlparse(input_url)
        if not parsed_url.netloc:
            logger.error(f"Invalid URL format for competitor {competitor.name}: {input_url}")
            return {"status": "error", "message": "Invalid URL format"}
        
        # Website existence check
        headers_check = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            response_check = requests.head(input_url, headers=headers_check, timeout=5)
            if response_check.status_code >= 500:
                logger.error(f"Website returned server error ({response_check.status_code}): {input_url}")
                return {"status": "error", "message": f"Server error {response_check.status_code}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Website unreachable: {input_url} - {str(e)}")
            return {"status": "error", "message": "Website unreachable"}
        
        # Call Firecrawl API
        api_url = "https://api.firecrawl.dev/v2/map"
        payload = {
            "url": input_url,
            "limit": 5000,
            "includeSubdomains": False,
            "sitemap": "include"
        }
        api_headers = {
            "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(api_url, json=payload, headers=api_headers)
        
        if response.status_code != 200:
            logger.error(f"Firecrawl API error: {response.text}")
            return {"status": "error", "message": "Firecrawl API error"}
        
        data = response.json()
        links = data.get("links", [])
        
        if not links:
            logger.warning(f"No links found for {competitor.name}")
            return {"status": "warning", "message": "No links found"}
        
        # Extract URLs from response
        extracted_urls = [item["url"] for item in links]
        
        # Store in database instead of text file
        extracted_links, created = ExtractedLinks.objects.update_or_create(
            competitor=competitor,
            defaults={'links': extracted_urls}
        )
        
        logger.info(f"✅ Extracted {len(extracted_urls)} links for {competitor.name}")
        return {
            "status": "success",
            "competitor": competitor.name,
            "links_count": len(extracted_urls)
        }
        
    except Competitor.DoesNotExist:
        logger.error(f"Competitor {competitor_id} not found")
        return {"status": "error", "message": "Competitor not found"}
    except Exception as e:
        logger.error(f"Error extracting links for competitor {competitor_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task
def scrape_competitor_html(competitor_id, use_filtered_links=False):
    """
    Scrape HTML content from competitor's links using Playwright.
    Based on Scrape_HTML.py logic.
    
    Args:
        competitor_id: ID of the Competitor
        use_filtered_links: If True, use FilteredLinks; otherwise use ExtractedLinks
    """
    from apps.monitoring.models import Competitor, ExtractedLinks, FilteredLinks, CompetitorHTML
    
    try:
        competitor = Competitor.objects.get(id=competitor_id, is_deleted=False)
        
        # Get links to scrape
        if use_filtered_links:
            link_obj = FilteredLinks.objects.filter(competitor=competitor).first()
        else:
            link_obj = ExtractedLinks.objects.filter(competitor=competitor).first()
        
        if not link_obj or not link_obj.links:
            logger.warning(f"No links found for {competitor.name}")
            return {"status": "warning", "message": "No links to scrape"}
        
        urls = link_obj.links
        scraped_count = 0
        
        # Use Playwright to scrape each URL
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ])
            
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
            )
            
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => false});"
            )
            
            page = context.new_page()
            
            for url in urls:
                try:
                    logger.info(f"🌐 Scraping: {url}")
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Get outer HTML and clean, remove CSS and inline styles
                    cleaned_html = page.evaluate("""
                        () => {
                            // Remove CSS files and <style> tags
                            document.querySelectorAll('style, link[rel="stylesheet"], link[type="text/css"]').forEach(n => n.remove());

                            // Remove inline style attributes
                            const all = document.querySelectorAll('*');
                            all.forEach(el => {
                                if (el.hasAttribute('style')) el.removeAttribute('style');
                            });

                            return document.documentElement.outerHTML;
                        }
                    """)
                    
                    soup = BeautifulSoup(cleaned_html, "html.parser")
                    pretty_html = soup.prettify()
                    
                    # Store in database instead of HTML file
                    CompetitorHTML.objects.update_or_create(
                        competitor=competitor,
                        url=url,
                        defaults={'html_content': pretty_html}
                    )
                    
                    scraped_count += 1
                    logger.info(f"✅ Saved HTML for: {url}")
                    
                except Exception as e:
                    logger.error(f"❌ Error scraping {url}: {str(e)}")
                    continue
            
            page.close()
            context.close()
            browser.close()
        
        logger.info(f"✅ Scraped {scraped_count}/{len(urls)} pages for {competitor.name}")
        return {
            "status": "success",
            "competitor": competitor.name,
            "scraped_count": scraped_count,
            "total_urls": len(urls)
        }
        
    except Competitor.DoesNotExist:
        logger.error(f"Competitor {competitor_id} not found")
        return {"status": "error", "message": "Competitor not found"}
    except Exception as e:
        logger.error(f"Error scraping HTML for competitor {competitor_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task
def extract_competitor_metadata(competitor_id):
    """
    Extract clean text and metadata from scraped HTML for RAG system.
    Based on json_of_html.py logic.
    
    Args:
        competitor_id: ID of the Competitor
    """
    from apps.monitoring.models import Competitor, CompetitorHTML, CompetitorMetadata
    
    def extract_clean_text(soup):
        """Extract and clean text from BeautifulSoup object."""
        # Remove non-visible garbage
        for tag in soup(["script", "style", "noscript", "svg", "iframe", "meta", "link"]):
            tag.extract()
        
        all_text = soup.get_text(separator="\n")
        
        # Clean multiple spaces, tabs, newlines
        lines = [re.sub(r"\s+", " ", line).strip() for line in all_text.split("\n")]
        
        cleaned = []
        seen = set()
        
        for line in lines:
            if len(line) < 3:
                continue
            # Remove bullet symbols, dashes, leading hyphens
            line = re.sub(r"^[\-\•\▪]+ ?", "", line)
            # Prevent duplicates
            key = hashlib.md5(line.lower().encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                cleaned.append(line)
        
        return cleaned
    
    try:
        competitor = Competitor.objects.get(id=competitor_id, is_deleted=False)
        html_objects = CompetitorHTML.objects.filter(competitor=competitor)
        
        if not html_objects.exists():
            logger.warning(f"No HTML content found for {competitor.name}")
            return {"status": "warning", "message": "No HTML content to process"}
        
        processed_count = 0
        
        for html_obj in html_objects:
            try:
                soup = BeautifulSoup(html_obj.html_content, "html.parser")
                
                # Extract clean content
                content_lines = extract_clean_text(soup)
                content_text = "\n".join(content_lines)
                
                # Extract title if available
                title = soup.title.string.strip() if soup.title and soup.title.string else None
                
                # Create metadata JSON object
                metadata = {
                    "url": html_obj.url,
                    "title": title,
                    "content": content_text,
                    "content_length": len(content_text),
                    "line_count": len(content_lines)
                }
                
                # Store in database instead of JSON file
                CompetitorMetadata.objects.update_or_create(
                    competitor=competitor,
                    url=html_obj.url,
                    defaults={'metadata': metadata}
                )
                
                processed_count += 1
                logger.info(f"✅ Processed metadata for: {html_obj.url}")
                
            except Exception as e:
                logger.error(f"❌ Error processing {html_obj.url}: {str(e)}")
                continue
        
        logger.info(f"✅ Processed {processed_count}/{html_objects.count()} pages for {competitor.name}")
        return {
            "status": "success",
            "competitor": competitor.name,
            "processed_count": processed_count,
            "total_html": html_objects.count()
        }
        
    except Competitor.DoesNotExist:
        logger.error(f"Competitor {competitor_id} not found")
        return {"status": "error", "message": "Competitor not found"}
    except Exception as e:
        logger.error(f"Error extracting metadata for competitor {competitor_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task
def run_full_scraping_pipeline(competitor_id, use_filtered_links=False):
    """
    Run the complete scraping pipeline for a competitor:
    1. Extract links (if not using filtered)
    2. Scrape HTML content
    3. Extract metadata for RAG
    
    Args:
        competitor_id: ID of the Competitor
        use_filtered_links: If True, skip link extraction and use FilteredLinks
    """
    from apps.monitoring.models import Competitor
    
    try:
        competitor = Competitor.objects.get(id=competitor_id, is_deleted=False)
        logger.info(f"🚀 Starting full scraping pipeline for {competitor.name}")
        
        results = {}
        
        # Step 1: Extract links (unless using filtered links)
        if not use_filtered_links:
            logger.info("Step 1: Extracting links...")
            results['link_extraction'] = extract_competitor_links(competitor_id)
        else:
            results['link_extraction'] = {"status": "skipped", "message": "Using filtered links"}
        
        # Step 2: Scrape HTML
        logger.info("Step 2: Scraping HTML...")
        results['html_scraping'] = scrape_competitor_html(competitor_id, use_filtered_links)
        
        # Step 3: Extract metadata
        logger.info("Step 3: Extracting metadata...")
        results['metadata_extraction'] = extract_competitor_metadata(competitor_id)
        
        logger.info(f"✅ Completed full pipeline for {competitor.name}")
        return {
            "status": "success",
            "competitor": competitor.name,
            "results": results
        }
        
    except Competitor.DoesNotExist:
        logger.error(f"Competitor {competitor_id} not found")
        return {"status": "error", "message": "Competitor not found"}
    except Exception as e:
        logger.error(f"Error in scraping pipeline for competitor {competitor_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task
def scrape_all_competitors():
    """Run full scraping pipeline for all active competitors."""
    from .models import ScrapingConfig
    
    active_configs = ScrapingConfig.objects.filter(is_active=True)
    
    for config in active_configs:
        scrape_competitor.delay(config.id)
    
    logger.info(f"Triggered scraping for {active_configs.count()} competitors")
