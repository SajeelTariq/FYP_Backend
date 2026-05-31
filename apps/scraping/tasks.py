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
import random
import hashlib
import json
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Maximum subpage links allowed per competitor (from settings, with fallback)
MAX_COMPETITOR_LINKS = getattr(
    __import__('django.conf', fromlist=['settings']).settings,
    'MAX_COMPETITOR_LINKS', 100
)


def extract_competitor_links_sync(competitor_id):
    """
    Synchronous version of link extraction for use during competitor creation.
    Returns result dict immediately instead of dispatching to Celery.
    Enforces MAX_COMPETITOR_LINKS limit.
    """
    from apps.monitoring.models import Competitor, ExtractedLinks
    
    try:
        competitor = Competitor.objects.get(id=competitor_id, is_deleted=False)
        input_url = competitor.website_base_url
        
        if not input_url:
            return {"status": "warning", "message": "No website URL provided"}
        
        # Automatically add https:// if not present
        if not input_url.startswith(("http://", "https://")):
            input_url = "https://" + input_url
        
        parsed_url = urlparse(input_url)
        if not parsed_url.netloc:
            return {"status": "error", "message": "Invalid URL format"}
        
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
            return {"status": "warning", "message": "No subpage links found for this website"}
        
        # Firecrawl /v2/map returns links as strings; normalize defensively in case format changes
        extracted_urls = []
        for link in links:
            if isinstance(link, str):
                extracted_urls.append(link)
            elif isinstance(link, dict):
                url_val = link.get('url') or link.get('link') or ''
                if url_val:
                    extracted_urls.append(url_val)
        
        # Enforce maximum link count
        if len(extracted_urls) > MAX_COMPETITOR_LINKS:
            logger.warning(
                f"Competitor {competitor.name} has {len(extracted_urls)} links, "
                f"exceeds the maximum of {MAX_COMPETITOR_LINKS}"
            )
            return {
                "status": "error",
                "message": (
                    f"This competitor's website has {len(extracted_urls)} subpage links, "
                    f"which exceeds the maximum allowed limit of {MAX_COMPETITOR_LINKS}. "
                    f"Cannot proceed with this competitor."
                ),
                "links_count": len(extracted_urls)
            }
        
        # Store in database
        ExtractedLinks.objects.update_or_create(
            competitor=competitor,
            defaults={'links': extracted_urls}
        )
        
        logger.info(f"Extracted {len(extracted_urls)} links for {competitor.name}")
        return {
            "status": "success",
            "competitor": competitor.name,
            "links_count": len(extracted_urls)
        }
        
    except Competitor.DoesNotExist:
        return {"status": "error", "message": "Competitor not found"}
    except Exception as e:
        logger.error(f"Error extracting links for competitor {competitor_id}: {str(e)}")
        return {"status": "error", "message": str(e)}


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
        
        # Firecrawl /v2/map returns links as strings; normalize defensively in case format changes
        extracted_urls = []
        for link in links:
            if isinstance(link, str):
                extracted_urls.append(link)
            elif isinstance(link, dict):
                url_val = link.get('url') or link.get('link') or ''
                if url_val:
                    extracted_urls.append(url_val)
        
        # Enforce maximum link count
        if len(extracted_urls) > MAX_COMPETITOR_LINKS:
            logger.warning(
                f"Competitor {competitor.name} has {len(extracted_urls)} links, "
                f"exceeds the maximum of {MAX_COMPETITOR_LINKS}"
            )
            return {
                "status": "error",
                "message": (
                    f"This competitor's website has {len(extracted_urls)} subpage links, "
                    f"which exceeds the maximum allowed limit of {MAX_COMPETITOR_LINKS}. "
                    f"Cannot proceed with this competitor."
                ),
                "links_count": len(extracted_urls)
            }
        
        # Store in database
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
        
        # Use Playwright to scrape each URL — fresh browser per URL to avoid
        # bot-detection fingerprinting from shared browser sessions.
        for url in urls:
            try:
                logger.info(f"🌐 Scraping: {url}")
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
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)

                    # Get outer HTML and clean, remove CSS and inline styles
                    cleaned_html = page.evaluate("""
                        () => {
                            document.querySelectorAll('style, link[rel="stylesheet"], link[type="text/css"]').forEach(n => n.remove());
                            const all = document.querySelectorAll('*');
                            all.forEach(el => {
                                if (el.hasAttribute('style')) el.removeAttribute('style');
                            });
                            return document.documentElement.outerHTML;
                        }
                    """)

                    page.close()
                    context.close()
                    browser.close()

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
def run_initial_pipeline(competitor_id):
    """
    Triggered immediately when a new competitor is added (after links are already extracted).
    Runs HTML scraping → initial snapshots → metadata extraction → ChromaDB embeddings
    so RAG is ready without waiting for the nightly cron.

    Updates competitor.onboarding_status at each step so the frontend can show progress.
    """
    from apps.monitoring.models import Competitor, ExtractedLinks

    try:
        comp = Competitor.objects.get(id=competitor_id, is_deleted=False)

        link_obj = ExtractedLinks.objects.filter(competitor=comp).first()
        if not link_obj or not link_obj.links:
            comp.onboarding_status = 'error'
            comp.onboarding_error = 'No links available to scrape.'
            comp.save(update_fields=['onboarding_status', 'onboarding_error'])
            logger.warning(f"[InitialPipeline] {comp.name}: no links found, aborting")
            return

        urls = link_obj.links
        logger.info(f"[InitialPipeline] {comp.name}: starting with {len(urls)} links")

        # Step 1 — Scrape HTML (status already set to 'scraping' by views.py)
        _step2_scrape_html(comp, urls)

        # Step 2 — Create initial snapshots (marked as onboarding, excluded from change feed)
        _step3_detect_changes_and_summarize(comp, urls, is_onboarding=True)

        # Step 3 — Extract clean text + update embeddings
        comp.onboarding_status = 'indexing'
        comp.save(update_fields=['onboarding_status'])

        pages_indexed = _step4_extract_clean_text(comp, urls)
        embed_result  = _step5_update_embeddings(comp)

        comp.onboarding_status = 'ready'
        if embed_result.get('added', 0) == 0:
            comp.onboarding_error = (
                "Website content could not be indexed — pages may be blocking automated access. "
                "The competitor is still being monitored for changes, but the AI assistant "
                "will not have website knowledge for this competitor until re-indexing succeeds."
            )
            logger.warning(f"[InitialPipeline] {comp.name}: completed but 0 chunks indexed ({pages_indexed} pages processed)")
        else:
            comp.onboarding_error = ''
            logger.info(f"[InitialPipeline] {comp.name}: completed — RAG ready ({embed_result['added']} chunks)")
        comp.save(update_fields=['onboarding_status', 'onboarding_error'])

    except Competitor.DoesNotExist:
        logger.error(f"[InitialPipeline] Competitor {competitor_id} not found")
    except Exception as e:
        logger.error(f"[InitialPipeline] Failed for competitor {competitor_id}: {e}")
        try:
            comp.onboarding_status = 'error'
            comp.onboarding_error = str(e)[:500]
            comp.save(update_fields=['onboarding_status', 'onboarding_error'])
        except Exception:
            pass


@shared_task
def scrape_all_competitors():
    """Run full scraping pipeline for all active competitors."""
    from .models import ScrapingConfig
    
    active_configs = ScrapingConfig.objects.filter(is_active=True)
    
    for config in active_configs:
        scrape_competitor.delay(config.id)
    
    logger.info(f"Triggered scraping for {active_configs.count()} competitors")


# ──────────────────────────────────────────────────────────────────────
# Daily Monitoring Pipeline (Cron Job)
# ──────────────────────────────────────────────────────────────────────


def _call_openai_llm(prompt: str) -> str:
    """Call OpenAI API (GPT-4o-mini) to generate a summary."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return "LLM summary unavailable (no API key configured)"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 600,
    }
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenAI LLM error: {e}")
        return f"LLM summary generation failed: {e}"


def _step1_refresh_links(competitor):
    """
    Step 1 – Re-fetch sub-links via Firecrawl, compare with stored links,
    and flag new/removed URLs.  Returns (new_links, removed_links, all_current_links).
    """
    from apps.monitoring.models import ExtractedLinks

    input_url = competitor.website_base_url
    if not input_url:
        return [], [], []

    if not input_url.startswith(("http://", "https://")):
        input_url = "https://" + input_url

    api_url = "https://api.firecrawl.dev/v2/map"
    payload = {
        "url": input_url,
        "limit": 5000,
        "includeSubdomains": False,
        "sitemap": "include",
    }
    api_headers = {
        "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(api_url, json=payload, headers=api_headers, timeout=60)
        if response.status_code != 200:
            logger.error(f"Firecrawl API error for {competitor.name}: {response.text}")
            return [], [], []

        current_links = response.json().get("links", [])
    except Exception as e:
        logger.error(f"Firecrawl request failed for {competitor.name}: {e}")
        return [], [], []

    # Normalize to strings — Firecrawl v1 returns dicts, v2/map may vary
    def _to_url_str(item):
        if isinstance(item, dict):
            return item.get("url") or item.get("href") or str(item)
        return str(item)

    current_links = [_to_url_str(l) for l in current_links]

    # Enforce max links
    max_links = getattr(settings, "MAX_COMPETITOR_LINKS", 500)
    if len(current_links) > max_links:
        logger.warning(
            f"{competitor.name} has {len(current_links)} links, trimming to {max_links}"
        )
        current_links = current_links[:max_links]

    # Compare with previously stored links
    stored_obj = ExtractedLinks.objects.filter(competitor=competitor).first()
    stored_links = set(_to_url_str(l) for l in stored_obj.links) if stored_obj else set()
    current_set = set(current_links)

    new_links = list(current_set - stored_links)
    removed_links = list(stored_links - current_set)

    # Persist updated links
    ExtractedLinks.objects.update_or_create(
        competitor=competitor,
        defaults={"links": current_links},
    )

    logger.info(
        f"[Step1] {competitor.name}: {len(current_links)} links "
        f"(+{len(new_links)} new, -{len(removed_links)} removed)"
    )
    return new_links, removed_links, current_links


def _is_bot_challenge_page(html: str) -> bool:
    """Return True if the page is a bot-detection / challenge wall (e.g. Cloudflare)."""
    markers = [
        "cf-chl-opt",           # Cloudflare managed challenge JS object
        "challenge-platform",   # Cloudflare challenge script path
        "Enable JavaScript and cookies to continue",  # CF challenge noscript text
        "Just a moment",        # Cloudflare page title
        "_cf_chl_opt",          # Cloudflare challenge option variable
    ]
    lower = html[:4000]  # Only check the head of the page — fast
    return any(m in lower for m in markers)


def _step2_scrape_html(competitor, urls_to_scrape):
    """
    Step 2 – Scrape raw HTML for each URL using Playwright.
    Stores in CompetitorHTML (update_or_create).
    Returns count of successfully scraped pages.

    Uses sync Playwright with a fresh browser+context+page per URL so each
    request has a completely clean fingerprint.  Bot-challenge pages
    (Cloudflare etc.) are detected and discarded rather than saved as garbage.
    """
    from apps.monitoring.models import CompetitorHTML

    if not urls_to_scrape:
        return 0

    competitor_name = competitor.name
    scraped_html = {}

    for url in urls_to_scrape:
        if isinstance(url, dict):
            url = url.get('url') or url.get('link') or ''
        if not url or not isinstance(url, str):
            continue
        try:
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
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                cleaned_html = page.evaluate("""
                    () => {
                        document.querySelectorAll('style, link[rel="stylesheet"], link[type="text/css"]').forEach(n => n.remove());
                        const all = document.querySelectorAll('*');
                        all.forEach(el => {
                            if (el.hasAttribute('style')) el.removeAttribute('style');
                        });
                        return document.documentElement.outerHTML;
                    }
                """)

                page.close()
                context.close()
                browser.close()

            # Discard bot-challenge / firewall pages
            if _is_bot_challenge_page(cleaned_html):
                logger.warning(f"[Step2] Bot challenge detected, skipping: {url}")
                continue

            soup = BeautifulSoup(cleaned_html, "html.parser")
            scraped_html[url] = soup.prettify()

        except Exception as e:
            logger.error(f"[Step2] Error scraping {url}: {e}")

    # ORM writes happen after all scraping is done
    for url, html in scraped_html.items():
        CompetitorHTML.objects.update_or_create(
            competitor=competitor,
            url=url,
            defaults={"html_content": html},
        )

    scraped = len(scraped_html)
    skipped = len(urls_to_scrape) - scraped
    if skipped:
        logger.warning(f"[Step2] {competitor_name}: {skipped} URLs skipped (bot protection)")
    logger.info(f"[Step2] {competitor_name}: scraped {scraped}/{len(urls_to_scrape)} pages")
    return scraped


def _extract_visible_text_lines(html_content):
    """Extract visible text lines from HTML, stripping all tags and invisible elements."""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "meta", "link", "head"]):
        tag.extract()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return [line for line in lines if len(line) > 2]


def _step3_detect_changes_and_summarize(competitor, urls_to_check, is_onboarding=False):
    """
    Step 3 – For each URL:
      a) Compute SHA-256 of current HTML (from CompetitorHTML)
      b) Compare with latest HTMLSnapshot
      c) If changed: create new snapshot, diff visible text (not raw HTML),
         classify as critical/non_critical/technical, call LLM for business summary,
         store HTMLDifference, increment Competitor.change_count

    is_onboarding=True when called from run_initial_pipeline (first-time setup).
    Those first-time snapshot records are marked is_onboarding_snapshot=True and
    excluded from the website change feed so they don't create noise.
    Returns number of changes detected.
    """
    import json as _json
    from apps.monitoring.models import CompetitorHTML, HTMLSnapshot, HTMLDifference

    if not urls_to_check:
        return 0

    changes_detected = 0

    for url in urls_to_check:
        html_obj = CompetitorHTML.objects.filter(competitor=competitor, url=url).first()
        if not html_obj:
            continue

        current_html = html_obj.html_content
        current_hash = hashlib.sha256(current_html.encode("utf-8")).hexdigest()

        latest_snapshot = (
            HTMLSnapshot.objects.filter(competitor=competitor, url=url)
            .order_by("-snapshot_at")
            .first()
        )

        is_first_time = latest_snapshot is None
        has_changed = is_first_time or latest_snapshot.content_hash != current_hash

        if not has_changed:
            continue

        new_snapshot = HTMLSnapshot.objects.create(
            competitor=competitor,
            url=url,
            html_content=current_html,
            content_hash=current_hash,
        )

        if is_first_time:
            HTMLDifference.objects.create(
                competitor=competitor,
                url=url,
                old_snapshot=None,
                new_snapshot=new_snapshot,
                change_type="added",
                diff_summary={"note": "Initial snapshot recorded"},
                detailed_diff=[],
                is_significant=False,
                change_category="technical",
                llm_summary="Initial snapshot — no previous version to compare.",
                is_onboarding_snapshot=is_onboarding,
            )
            # Onboarding snapshots don't count as detected changes
            if not is_onboarding:
                changes_detected += 1
            continue

        # ── Compute raw HTML diff (stored for reference) ──
        old_lines = latest_snapshot.html_content.splitlines()
        new_lines = current_html.splitlines()
        sm_raw = SequenceMatcher(None, old_lines, new_lines)

        added_count = 0
        removed_count = 0
        diff_blocks = []
        for tag, i1, i2, j1, j2 in sm_raw.get_opcodes():
            if tag == "equal":
                continue
            block = {"type": tag, "old_range": [i1, i2], "new_range": [j1, j2]}
            if tag in ("replace", "delete"):
                removed_count += i2 - i1
            if tag in ("replace", "insert"):
                added_count += j2 - j1
            diff_blocks.append(block)

        if not diff_blocks:
            continue

        if removed_count == 0:
            change_type = "added"
        elif added_count == 0:
            change_type = "removed"
        else:
            change_type = "modified"

        diff_summary = {
            "added_lines": added_count,
            "removed_lines": removed_count,
            "total_blocks": len(diff_blocks),
        }

        # ── Diff visible text to determine real content change ──
        old_text_lines = _extract_visible_text_lines(latest_snapshot.html_content)
        new_text_lines = _extract_visible_text_lines(current_html)
        sm_text = SequenceMatcher(None, old_text_lines, new_text_lines)

        text_diff_parts = []
        for tag, i1, i2, j1, j2 in sm_text.get_opcodes():
            if tag == "equal":
                continue
            if tag in ("replace", "delete"):
                old_slice = old_text_lines[i1:i2]
                text_diff_parts.append("REMOVED:\n" + "\n".join(old_slice[:15]))
            if tag in ("replace", "insert"):
                new_slice = new_text_lines[j1:j2]
                text_diff_parts.append("ADDED:\n" + "\n".join(new_slice[:15]))

        # ── Classify and summarize ──
        if not text_diff_parts:
            # HTML structure changed but no visible text affected — purely technical
            change_category = "technical"
            is_significant = False
            llm_summary = "Technical update — no visible content changes detected (script or structural HTML only)."
        else:
            text_diff_context = "\n---\n".join(text_diff_parts[:8])
            llm_prompt = (
                f"You are analyzing website changes for a competitor intelligence platform.\n"
                f"Competitor: {competitor.name}\n"
                f"Page: {url}\n\n"
                f"The following visible text changes were detected:\n\n"
                f"{text_diff_context}\n\n"
                f"Tasks:\n"
                f"1. Classify as 'critical' or 'non_critical':\n"
                f"   - critical: price changes, product launches or removals, new features, "
                f"promotions, major announcements, strategic content changes\n"
                f"   - non_critical: minor text tweaks, updated dates, small wording "
                f"adjustments, minor navigation changes\n"
                f"2. Write a 1-2 sentence plain-English summary for a business user. "
                f"No HTML, no technical terms. Focus on the market or business impact.\n\n"
                f"Respond ONLY in this exact JSON format:\n"
                f'{{"category": "critical", "summary": "your summary here"}}'
            )
            raw_response = _call_openai_llm(llm_prompt)

            try:
                # Strip markdown code fences if the LLM wrapped the JSON
                clean = raw_response.strip().strip("```json").strip("```").strip()
                parsed = _json.loads(clean)
                change_category = parsed.get("category", "non_critical")
                if change_category not in ("critical", "non_critical"):
                    change_category = "non_critical"
                llm_summary = parsed.get("summary", raw_response)
            except Exception:
                change_category = "critical" if "critical" in raw_response.lower() else "non_critical"
                llm_summary = raw_response

            is_significant = (change_category == "critical")

        HTMLDifference.objects.create(
            competitor=competitor,
            url=url,
            old_snapshot=latest_snapshot,
            new_snapshot=new_snapshot,
            change_type=change_type,
            diff_summary=diff_summary,
            detailed_diff=diff_blocks,
            is_significant=is_significant,
            change_category=change_category,
            llm_summary=llm_summary,
        )

        changes_detected += 1

    if changes_detected > 0:
        from django.db.models import F
        from apps.monitoring.models import Competitor as CompetitorModel

        CompetitorModel.objects.filter(pk=competitor.pk).update(
            change_count=F("change_count") + changes_detected
        )
        competitor.refresh_from_db()

    logger.info(f"[Step3] {competitor.name}: {changes_detected} changes detected")
    return changes_detected


def _step4_extract_clean_text(competitor, urls_to_process):
    """
    Step 4 – Extract clean text from CompetitorHTML → store in CompetitorMetadata.
    Reuses the same logic as extract_competitor_metadata but scoped to given URLs.
    """
    from apps.monitoring.models import CompetitorHTML, CompetitorMetadata

    if not urls_to_process:
        return 0

    processed = 0
    for url in urls_to_process:
        html_obj = CompetitorHTML.objects.filter(competitor=competitor, url=url).first()
        if not html_obj:
            continue

        try:
            soup = BeautifulSoup(html_obj.html_content, "html.parser")
            # Remove non-visible elements
            for tag in soup(["script", "style", "noscript", "svg", "iframe", "meta", "link"]):
                tag.extract()

            all_text = soup.get_text(separator="\n")
            lines = [re.sub(r"\s+", " ", line).strip() for line in all_text.split("\n")]

            cleaned = []
            seen = set()
            for line in lines:
                if len(line) < 3:
                    continue
                line = re.sub(r"^[\-\•\▪]+ ?", "", line)
                key = hashlib.md5(line.lower().encode()).hexdigest()
                if key not in seen:
                    seen.add(key)
                    cleaned.append(line)

            content_text = "\n".join(cleaned)
            title = soup.title.string.strip() if soup.title and soup.title.string else None

            metadata = {
                "url": url,
                "title": title,
                "content": content_text,
                "content_length": len(content_text),
                "line_count": len(cleaned),
            }

            CompetitorMetadata.objects.update_or_create(
                competitor=competitor,
                url=url,
                defaults={"metadata": metadata},
            )
            processed += 1
        except Exception as e:
            logger.error(f"[Step4] Error processing {url}: {e}")
            continue

    logger.info(f"[Step4] {competitor.name}: processed {processed}/{len(urls_to_process)} pages")
    return processed


def _step5_update_embeddings(competitor):
    """
    Step 5 – Re-embed this competitor's data into ChromaDB from CompetitorMetadata.
    Deletes existing chunks for this competitor and re-ingests from DB.
    """
    try:
        from apps.rag.rag_service_chromadb import RAGServiceChroma

        rag_service = RAGServiceChroma()
        result = rag_service.ingest_competitor_from_db(competitor, user_id=competitor.user_id)
        logger.info(
            f"[Step5] {competitor.name}: "
            f"{result.get('added', 0)} chunks added, "
            f"{result.get('deleted', 0)} old chunks removed"
        )
        return result
    except Exception as e:
        logger.error(f"[Step5] Embedding update failed for {competitor.name}: {e}")
        return {"added": 0, "deleted": 0, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────
# News Fetching Pipeline (Every 6 Hours)
# ──────────────────────────────────────────────────────────────────────


_TLD_TO_COUNTRY = {
    'pk': ('PK', 'en-PK', 'Pakistan'),
    'in': ('IN', 'en-IN', 'India'),
    'uk': ('GB', 'en-GB', 'UK'),
    'co.uk': ('GB', 'en-GB', 'UK'),
    'au': ('AU', 'en-AU', 'Australia'),
    'co.au': ('AU', 'en-AU', 'Australia'),
    'ca': ('CA', 'en-CA', 'Canada'),
    'de': ('DE', 'de-DE', 'Germany'),
    'fr': ('FR', 'fr-FR', 'France'),
    'ae': ('AE', 'en-AE', 'UAE'),
    'sa': ('SA', 'ar-SA', 'Saudi Arabia'),
    'bd': ('BD', 'en-BD', 'Bangladesh'),
    'ng': ('NG', 'en-NG', 'Nigeria'),
    'za': ('ZA', 'en-ZA', 'South Africa'),
}


_COUNTRY_NAMES_IN_DOMAIN = {
    'pakistan': ('PK', 'en-PK', 'Pakistan'),
    'india':    ('IN', 'en-IN', 'India'),
    'australia':('AU', 'en-AU', 'Australia'),
    'canada':   ('CA', 'en-CA', 'Canada'),
    'germany':  ('DE', 'de-DE', 'Germany'),
    'france':   ('FR', 'fr-FR', 'France'),
    'uae':      ('AE', 'en-AE', 'UAE'),
    'nigeria':  ('NG', 'en-NG', 'Nigeria'),
}

_PATH_COUNTRY_CODE = {
    'pk': ('PK', 'en-PK', 'Pakistan'),
    'in': ('IN', 'en-IN', 'India'),
    'gb': ('GB', 'en-GB', 'UK'),
    'uk': ('GB', 'en-GB', 'UK'),
    'au': ('AU', 'en-AU', 'Australia'),
    'ca': ('CA', 'en-CA', 'Canada'),
    'de': ('DE', 'de-DE', 'Germany'),
    'fr': ('FR', 'fr-FR', 'France'),
    'ae': ('AE', 'en-AE', 'UAE'),
    'sa': ('SA', 'ar-SA', 'Saudi Arabia'),
    'bd': ('BD', 'en-BD', 'Bangladesh'),
    'ng': ('NG', 'en-NG', 'Nigeria'),
    'za': ('ZA', 'en-ZA', 'South Africa'),
}


def _extract_domain_query(url: str):
    """Extract domain name + country params from a URL.

    Handles three patterns:
      1. Country TLD:        honda.com.pk   → 'honda Pakistan', PK
      2. Country in domain:  suzukipakistan.com → 'suzuki Pakistan', PK
      3. Country in path:    kia.com/pk     → 'kia Pakistan', PK
      4. Generic .com:       microsoft.com  → 'microsoft', US
    """
    try:
        parsed = urlparse(url)
        netloc = (parsed.netloc or url).lower().replace('www.', '')
        parts = netloc.split('.')

        # 1. Country TLD (e.g. .com.pk / .co.uk)
        two_part = '.'.join(parts[-2:]) if len(parts) >= 2 else ''
        one_part = parts[-1] if parts else ''
        country_data = _TLD_TO_COUNTRY.get(two_part) or _TLD_TO_COUNTRY.get(one_part)
        if country_data:
            gl, hl, country_name = country_data
            return f"{parts[0]} {country_name}", gl, hl

        domain_name = parts[0]

        # 2. Country name embedded in domain (e.g. suzukipakistan)
        for keyword, (gl, hl, country_name) in _COUNTRY_NAMES_IN_DOMAIN.items():
            if domain_name.endswith(keyword):
                clean = domain_name[: -len(keyword)].rstrip('-')
                return f"{clean} {country_name}", gl, hl

        # 3. Country code in URL path (e.g. kia.com/pk)
        path_parts = [p for p in parsed.path.lower().split('/') if p]
        if path_parts:
            country_data = _PATH_COUNTRY_CODE.get(path_parts[0])
            if country_data:
                gl, hl, country_name = country_data
                return f"{domain_name} {country_name}", gl, hl

        # 4. Default — global .com
        return domain_name, 'US', 'en-US'

    except Exception:
        return '', 'US', 'en-US'


def _fetch_news_for_competitor(competitor, hours=2):
    """Fetch Google News RSS for a competitor using its domain name as the query.

    Args:
        competitor: Competitor instance
        hours: Only save articles published within this many hours (default 2 for
               scheduled runs). Pass hours=144 for the initial 6-day backfill.
    """
    import feedparser
    from urllib.parse import quote_plus
    from datetime import datetime, timedelta
    from apps.monitoring.models import NewsArticle

    base_url = competitor.website_base_url or ''
    query_term, gl, hl = _extract_domain_query(base_url)
    if not query_term:
        logger.warning(f"[NewsTask] {competitor.name}: no base URL — skipping")
        return

    cutoff = timezone.now() - timedelta(hours=hours)
    rss_url = (
        f"https://news.google.com/rss/search"
        f"?q={quote_plus(query_term)}&hl={hl}&gl={gl}&ceid={gl}:{hl.split('-')[0]}"
    )

    try:
        feed = feedparser.parse(rss_url)
        saved = 0
        for entry in feed.entries:
            published_at = None
            if getattr(entry, 'published_parsed', None):
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

            # Skip articles older than 6 days
            if published_at and published_at < cutoff:
                continue

            source = ''
            if hasattr(entry, 'source') and isinstance(entry.source, dict):
                source = entry.source.get('title', '')

            _, created = NewsArticle.objects.get_or_create(
                competitor=competitor,
                url=entry.link,
                defaults={
                    'title': entry.title,
                    'source': source,
                    'published_at': published_at,
                },
            )
            if created:
                saved += 1

        logger.info(f"[NewsTask] {competitor.name} (query: {query_term!r}): {saved} new articles saved")
    except Exception as e:
        logger.error(f"[NewsTask] Failed for {competitor.name}: {e}")


@shared_task
def fetch_initial_competitor_news(competitor_id):
    """
    One-time backfill triggered when a new competitor is created.
    Fetches last 6 days (144 hours) of news.
    """
    from apps.monitoring.models import Competitor
    try:
        comp = Competitor.objects.get(id=competitor_id, is_deleted=False)
        _fetch_news_for_competitor(comp, hours=144)
        logger.info(f"[NewsTask] Initial backfill done for {comp.name}")
    except Competitor.DoesNotExist:
        logger.error(f"[NewsTask] Competitor {competitor_id} not found for initial fetch")


@shared_task
def fetch_all_competitors_news():
    """
    Incremental news fetch — runs every 2 hours via Celery Beat.
    Only fetches articles published in the last 2 hours.
    """
    from apps.monitoring.models import Competitor

    competitors = Competitor.objects.filter(is_deleted=False)
    if not competitors.exists():
        logger.info("[NewsTask] No active competitors — skipping.")
        return {"status": "skipped"}

    for comp in competitors:
        _fetch_news_for_competitor(comp, hours=2)

    logger.info(f"[NewsTask] Incremental fetch done for {competitors.count()} competitors")
    return {"status": "completed", "competitors": competitors.count()}


@shared_task
def run_daily_monitoring():
    """
    Daily monitoring pipeline — runs for ALL active (non-deleted) competitors.

    Steps per competitor:
      1. Firecrawl sub-links refresh  → detect new/removed URLs
      2. Scrape raw HTML              → store in CompetitorHTML
      3. HTML diff + LLM summary      → store in HTMLDifference
      4. Clean text extraction         → store in CompetitorMetadata
      5. ChromaDB embedding update     → re-embed competitor data
    """
    from apps.monitoring.models import Competitor

    competitors = Competitor.objects.filter(is_deleted=False)
    if not competitors.exists():
        logger.info("[DailyMonitoring] No active competitors found — skipping.")
        return {"status": "skipped", "message": "No active competitors"}

    results = {}
    for comp in competitors:
        logger.info(f"[DailyMonitoring] ══ Starting pipeline for {comp.name} ══")
        comp_result = {}

        try:
            # Step 1: Refresh links
            new_links, removed_links, all_links = _step1_refresh_links(comp)
            comp_result["step1_links"] = {
                "total": len(all_links),
                "new": len(new_links),
                "removed": len(removed_links),
            }

            # Step 2: Scrape HTML for ALL current links
            scraped = _step2_scrape_html(comp, all_links)
            comp_result["step2_scrape"] = {"scraped": scraped, "total": len(all_links)}

            # Step 3: Detect changes & generate LLM summaries
            changes = _step3_detect_changes_and_summarize(comp, all_links)
            comp_result["step3_changes"] = changes

            # Step 4: Extract clean text for all pages
            processed = _step4_extract_clean_text(comp, all_links)
            comp_result["step4_metadata"] = processed

            # Step 5: Update ChromaDB embeddings
            embed_result = _step5_update_embeddings(comp)
            comp_result["step5_embeddings"] = embed_result

            comp_result["status"] = "success"
            logger.info(f"[DailyMonitoring] ══ Completed {comp.name} ══")

        except Exception as e:
            comp_result["status"] = "error"
            comp_result["error"] = str(e)
            logger.error(f"[DailyMonitoring] Pipeline failed for {comp.name}: {e}")

        results[comp.name] = comp_result

    logger.info(f"[DailyMonitoring] Finished all competitors: {list(results.keys())}")

    # Send email alerts to opted-in users
    try:
        from apps.accounts.email_service import send_website_change_alerts, send_new_pages_alerts
        send_website_change_alerts()
        send_new_pages_alerts()
    except Exception as exc:
        logger.error(f"[DailyMonitoring] Email alert dispatch failed: {exc}")

    return {"status": "completed", "results": results}
