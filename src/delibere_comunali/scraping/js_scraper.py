"""
JavaScript-aware scraper for sites that use client-side rendering for document downloads.
Used primarily for Halleyweb and other modern municipal platforms.
Optimized for production use with browser context management.
"""
import asyncio
import sys
import random
import time
from typing import List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import re

# Fix per il problema "I/O operation on closed pipe" di Playwright su Windows
# Ma gestiamo il NotImplementedError che può accadere con Python 3.13
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except (NotImplementedError, AttributeError):
        # Se WindowsSelectorEventLoopPolicy non è disponibile, continuiamo con il default
        pass

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from bs4 import BeautifulSoup
import urllib.parse as up


@dataclass
class ScrapeResult:
    html_content: str
    extracted_urls: List[str]
    page_title: str
    cookies: dict


class JSScraper:
    """
    A scraper capable of executing JavaScript to extract dynamically loaded content.
    Implements optimized browser context management for production use.
    """
    
    def __init__(self, timeout: int = 30000, download_dir: Optional[str] = None, delay_range: Tuple[float, float] = (1.5, 4.0)):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright is required for JavaScript-aware scraping. "
                "Install it with: pip install playwright\n"
                "Then run: playwright install"
            )
        self.timeout = timeout
        self.download_dir = Path(download_dir) if download_dir else None
        self.delay_range = delay_range  # Range for dynamic jitter
        
        # Browser management
        self.playwright_instance = None
        self.browser_instance = None
        self.active_context = None
        self.download_count = 0
        self.max_downloads_per_session = 50  # Reset browser every 50 downloads
        
        # Rate limiting and backoff tracking
        self.last_request_time = 0
        self.current_delay = delay_range[0]  # Start with minimum delay
        self.backoff_multiplier = 1.0  # Multiplier for exponential backoff
        self.max_backoff_delay = 60.0  # Maximum backoff delay (seconds)
    
    async def apply_rate_limit(self, is_error: bool = False):
        """
        Apply dynamic rate limiting with jitter and exponential backoff
        """
        if is_error:
            # Increase backoff multiplier on error
            self.backoff_multiplier = min(self.backoff_multiplier * 1.5, 10.0)
        else:
            # Gradually decrease backoff multiplier when things go smoothly
            self.backoff_multiplier = max(self.backoff_multiplier * 0.9, 1.0)
        
        # Calculate delay with jitter and backoff
        base_delay = self.current_delay * self.backoff_multiplier
        min_delay = max(base_delay * 0.7, self.delay_range[0])
        max_delay = min(base_delay * 1.3, self.delay_range[1] * self.backoff_multiplier)
        
        # Apply exponential backoff cap
        max_delay = min(max_delay, self.max_backoff_delay)
        
        # Calculate final delay with jitter
        final_delay = random.uniform(min_delay, max_delay)
        
        # Ensure minimum time between requests
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        sleep_time = max(final_delay - time_since_last, 0)
        
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def initialize_browser(self):
        """Initialize browser instance once"""
        if self.browser_instance is None:
            self.playwright_instance = await async_playwright().start()
            self.browser_instance = await self.playwright_instance.chromium.launch(headless=True)
        
        if self.active_context is None:
            self.active_context = await self.browser_instance.new_context(accept_downloads=True)
    
    async def close(self):
        """Closes the browser and playwright instance."""
        if self.active_context:
            try: await self.active_context.close()
            except Exception: pass
            self.active_context = None
        if self.browser_instance:
            try: await self.browser_instance.close()
            except Exception: pass
            self.browser_instance = None
        if self.playwright_instance:
            try: await self.playwright_instance.stop()
            except Exception: pass
            self.playwright_instance = None

    async def reset_browser_if_needed(self):
        """Reset browser if we've exceeded the download limit"""
        self.download_count += 1
        if self.download_count >= self.max_downloads_per_session:
            if self.active_context:
                await self.active_context.close()
            if self.browser_instance:
                await self.close() # Full close and restart
            self.browser_instance = None
            self.active_context = None
            self.download_count = 0
            await self.initialize_browser()
    
    async def scrape_page(self, url: str) -> ScrapeResult:
        """
        Scrape a page with JavaScript execution enabled.
        Uses shared browser context for efficiency.
        """
        await self.apply_rate_limit()  # Apply rate limiting before request
        
        await self.initialize_browser()
        
        page = await self.active_context.new_page()
        page.set_default_timeout(self.timeout)
        
        try:
            # Navigate to the page
            await page.goto(url, wait_until="networkidle")
            
            # Wait a bit for JavaScript to execute
            await page.wait_for_load_state("networkidle")
            
            # Get the fully rendered HTML
            html_content = await page.content()
            
            # Extract page title
            page_title = await page.title()
            
            # Get cookies if needed for subsequent requests
            cookies = await page.context.cookies()
            cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            # Extract URLs that might be hidden in JavaScript event handlers
            js_extracted_urls = await self._extract_js_urls(page)
            
            result = ScrapeResult(
                html_content=html_content,
                extracted_urls=js_extracted_urls,
                page_title=page_title,
                cookies=cookies_dict
            )
            
        except Exception as e:
            # Apply backoff on error
            await self.apply_rate_limit(is_error=True)
            raise e
        finally:
            await page.close()
            await self.reset_browser_if_needed()
        
        # Apply rate limiting after successful request
        await self.apply_rate_limit(is_error=False)
        
        return result

    async def download_attachments_from_page(self, url: str, download_dir: str) -> List[str]:
        """
        Download attachments from a page by simulating clicks and intercepting downloads.
        Optimized to reuse browser context.
        Implements brute-force strategy for Halleyweb to click potential download elements.
        """
        downloaded_files = []
        await self.initialize_browser()
        
        # Apply rate limiting before download attempt
        await self.apply_rate_limit()
        
        page = await self.active_context.new_page()
        page.set_default_timeout(self.timeout)
        
        try:
            # Navigate to the page
            await page.goto(url, wait_until="networkidle")
            
            # Enable network monitoring to intercept requests
            intercepted_requests = []
            
            def on_request(request):
                # Monitor for potential download requests
                if any(keyword in request.url.lower() for keyword in ['download', 'getdoc', 'documento', 'allegato', '.pdf', '.p7m']):
                    intercepted_requests.append({
                        'url': request.url,
                        'method': request.method,
                        'timestamp': time.time()
                    })
            
            page.on("request", on_request)
            
            # Wait for content to load
            await page.wait_for_load_state("networkidle")
            
            # BRUTE-FORCE STRATEGY FOR HALLEYWEB: Actively click potential download elements
            # Look for typical Halleyweb download patterns and click them
            halleyweb_patterns = [
                "a[href*='javascript:']",  # JavaScript links
                "a:has-text('Allegato')",  # Elements containing 'Allegato'
                "a:has-text('Documento')",  # Elements containing 'Documento' 
                "a:has-text('PDF')",       # Elements containing 'PDF'
                "a:has(img[src*='pdf'])",  # Links with PDF icons
                "a:has(svg:has-text('PDF'))",  # SVG elements with PDF text
                "button:has-text('Scarica')",  # Download buttons
                "span:has-text('Allegato')",   # Span with Allegato text
                "[onclick*='scarica']",        # Elements with scarica in onclick
                "[onclick*='download']",       # Elements with download in onclick
                "[onclick*='getdoc']",         # Elements with getdoc in onclick
            ]
            
            # NEW: Target the specific Halleyweb patterns seen in the screenshots
            # Directly target the problematic 'javascript:void(0);' links and PDF extensions
            specific_halleyweb_locators = [
                "a[href='javascript:void(0);']",  # The exact problematic pattern from screenshots
                "a:has-text('.PDF')",            # PDF extension in uppercase
                "a:has-text('.pdf')",            # PDF extension in lowercase
                "a:has-text('.P7M')",            # P7M extension in uppercase
                "a:has-text('.p7m')",            # P7M extension in lowercase
                "a:has-text('Documento')",       # The "Documento" text link from screenshots
            ]
            
            # Track which downloads we've already captured to avoid duplicates
            captured_download_urls = set()
            
            for pattern in halleyweb_patterns:
                try:
                    elements = await page.locator(pattern).all()
                    print(f"Found {len(elements)} elements matching pattern: {pattern}")
                    
                    for i, element in enumerate(elements):
                        try:
                            # Check if element is visible and clickable
                            is_visible = await element.is_visible()
                            if not is_visible:
                                continue
                            
                            # Get element text and attributes for debugging
                            element_text = await element.text_content()
                            element_href = await element.get_attribute("href") or ""
                            element_onclick = await element.get_attribute("onclick") or ""
                            
                            print(f"Attempting to interact with element {i}: text='{element_text[:50]}...', href='{element_href}', onclick='{element_onclick[:50]}...'")
                            
                            # Apply rate limiting between clicks
                            await self.apply_rate_limit()
                            
                            # Try to click the element and intercept any download
                            try:
                                with page.expect_download(timeout=10000) as download_info:
                                    await element.click(force=True)
                                    await page.wait_for_timeout(2000)  # Wait for download to start
                                    
                                    download = await download_info.value
                                    filename = download.suggested_filename or f"attachment_{int(time.time())}_{len(downloaded_files)}.pdf"
                                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                                    
                                    filepath = Path(download_dir) / filename
                                    await download.save_as(str(filepath))
                                    downloaded_files.append(str(filepath))
                                    print(f"Successfully downloaded via brute-force click: {filename}")
                                    
                                    # Break inner loop to avoid multiple downloads from same click
                                    break
                                    
                            except Exception as click_error:
                                print(f"Click did not trigger download for element {i}: {click_error}")
                                # This is expected for many elements, continue to next
                                
                        except Exception as element_error:
                            print(f"Error processing element {i}: {element_error}")
                            continue
                            
                except Exception as pattern_error:
                    print(f"Pattern {pattern} caused error: {pattern_error}")
                    continue  # Continue with next pattern
            
            # Also try the network sniffing approach as backup
            attachment_elements = await page.evaluate("""
                () => {
                    const elements = [];
                    const allElements = document.querySelectorAll('*');
                    
                    for (const el of allElements) {
                        const text = (el.textContent || '').toLowerCase();
                        const onclick = (el.getAttribute('onclick') || '').toLowerCase();
                        const href = (el.getAttribute('href') || '').toLowerCase();
                        
                        // Look for common Halleyweb patterns
                        if (text.includes('documento') || text.includes('allegato') || 
                            text.includes('scarica') || text.includes('pdf') ||
                            onclick.includes('scarica') || onclick.includes('download') || onclick.includes('getdoc') ||
                            href.includes('getdoc') || href.includes('download') ||
                            href.includes('javascript:void(0)')) {
                            
                            elements.push({
                                text: el.textContent || '',
                                onclick: el.getAttribute('onclick'),
                                href: el.getAttribute('href'),
                                tagName: el.tagName,
                                selector: el.tagName.toLowerCase() + 
                                         (el.id ? '#' + el.id : '') + 
                                         (el.className ? '.' + el.className.split(' ')[0] : '')
                            });
                        }
                    }
                    return elements;
                }
            """)
            
            # Process potential attachment elements with network sniffing approach
            for element_info in attachment_elements:
                original_request_count = len(intercepted_requests)
                
                # Try to trigger the action that would cause download request
                if element_info['onclick']:
                    try:
                        # Execute the onclick function without necessarily clicking
                        await page.evaluate(f"""() => {{ 
                            try {{ 
                                {element_info['onclick']} 
                            }} catch(e) {{ 
                                console.log('Error executing onclick:', e.message); 
                            }}
                        }}""")
                        
                        # Wait briefly for any requests to be made
                        await page.wait_for_timeout(2000)
                    except:
                        pass  # Continue to next element if this fails
                
                # Check if any new requests were intercepted
                new_requests = intercepted_requests[original_request_count:]
                for req in new_requests:
                    if req['url'] not in captured_download_urls and any(ext in req['url'].lower() for ext in ['.pdf', '.p7m', '.doc', '.docx']):
                        captured_download_urls.add(req['url'])
                        
                        # Try to access this URL directly
                        try:
                            # Apply rate limiting before download attempt
                            await self.apply_rate_limit()
                            
                            # Create a temporary page just for this download
                            temp_page = await self.active_context.new_page()
                            temp_page.set_default_timeout(15000)
                            
                            with temp_page.expect_download() as download_info:
                                await temp_page.goto(req['url'], wait_until="domcontentloaded")
                                await temp_page.wait_for_timeout(1000)
                                
                                download = await download_info.value
                                filename = download.suggested_filename or f"attachment_{int(time.time())}_{len(downloaded_files)}.pdf"
                                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                                
                                filepath = Path(download_dir) / filename
                                await download.save_as(str(filepath))
                                downloaded_files.append(str(filepath))
                                print(f"Successfully downloaded via network sniffing: {filename}")
                                
                            await temp_page.close()
                            break  # Break to avoid multiple downloads from same trigger
                        except Exception as e:
                            print(f"Direct download failed for {req['url']}: {e}")
                            # Apply backoff on download failure
                            await self.apply_rate_limit(is_error=True)
            
        except Exception as e:
            print(f"Error downloading attachments from {url}: {e}")
            await self.apply_rate_limit(is_error=True)
            raise e
        finally:
            await page.close()
            await self.reset_browser_if_needed()
        
        return downloaded_files

    async def _extract_js_urls(self, page) -> List[str]:
        """
        Extract URLs from JavaScript event handlers and dynamic content.
        """
        # Execute JavaScript to find all onclick handlers and other event handlers
        urls = await page.evaluate("""
            () => {
                const urls = [];
                
                // Find all elements with onclick attributes that might contain download URLs
                const elementsWithOnclick = document.querySelectorAll('[onclick]');
                for (const elem of elementsWithOnclick) {
                    const onclick = elem.getAttribute('onclick');
                    if (onclick) {
                        // Look for common patterns in onclick handlers
                        const matches = onclick.match(/['"](.*?\\\\.(pdf|doc|docx|zip|p7m|php|download|getdoc).*?)['"]/gi);
                        if (matches) {
                            matches.forEach(match => {
                                // Remove quotes and extract the URL
                                const cleanUrl = match.replace(/['"]/g, '');
                                if (cleanUrl && !urls.includes(cleanUrl)) {
                                    urls.push(cleanUrl);
                                }
                            });
                        }
                    }
                }
                
                // Also look for elements with data attributes that might contain URLs
                const elementsWithData = document.querySelectorAll('[data-href], [data-url], [data-file]');
                for (const elem of elementsWithData) {
                    const dataHref = elem.getAttribute('data-href');
                    const dataUrl = elem.getAttribute('data-url');
                    const dataFile = elem.getAttribute('data-file');
                    
                    [dataHref, dataUrl, dataFile].forEach(attr => {
                        if (attr && /\\\\.(pdf|doc|docx|zip|p7m|php)/i.test(attr)) {
                            if (!urls.includes(attr)) {
                                urls.push(attr);
                            }
                        }
                    });
                }
                
                // Look for links that are constructed via JavaScript
                const allLinks = document.querySelectorAll('a');
                for (const link of allLinks) {
                    const href = link.getAttribute('href');
                    if (href && (href.includes('getdoc') || href.includes('download') || href.includes('pdf'))) {
                        if (!urls.includes(href)) {
                            urls.push(href);
                        }
                    }
                }
                
                return urls;
            }
        """)
        
        return urls if urls else []


def is_halleyweb_url(url: str) -> bool:
    """Check if the URL belongs to a Halleyweb platform."""
    return 'halleyweb' in url.lower()


def should_use_js_scraper(url: str) -> bool:
    """Determine if JavaScript-enabled scraping should be used for this URL."""
    return is_halleyweb_url(url)


async def _scrape_page_in_context(url: str, timeout: int):
    scraper = JSScraper(timeout)
    try:
        return await scraper.scrape_page(url)
    finally:
        await scraper.close()

def sync_scrape_page(url: str, timeout: int = 30000) -> Optional[ScrapeResult]:
    """
    Synchronous wrapper for the async scrape_page function.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None

    try:
        return asyncio.run(_scrape_page_in_context(url, timeout))
    except Exception as e:
        # Log the actual error for better debugging
        print(f"ERROR in sync_scrape_page for {url}: {e}", file=sys.stderr)
        # Fall back to regular requests if Playwright fails
        return None

async def _download_attachments_in_context(url: str, download_dir: str, timeout: int):
    scraper = JSScraper(timeout, download_dir)
    try:
        return await scraper.download_attachments_from_page(url, download_dir)
    finally:
        await scraper.close()
        
def download_attachments_sync(url: str, download_dir: str, timeout: int = 30000) -> List[str]:
    """
    Synchronous wrapper for downloading attachments from a page.
    Includes enhanced fallback when Playwright is unavailable.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return []
    
    try:
        return asyncio.run(_download_attachments_in_context(url, download_dir, timeout))
    except Exception as e:
        print(f"Attachment download failed: {e}")
        return []