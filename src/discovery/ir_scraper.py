import re
import datetime
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger
from src.utils.rate_limiter import polite_get
from src.discovery.vendor_classifier import classify_vendor_from_html, classify_vendor_from_url
from src.utils.date_parser import parse_call_datetime_to_utc
from src.discovery.sec_edgar import extract_fiscal_period_from_text, extract_call_datetime_from_text, is_non_earnings_event

logger = setup_logger("ir_scraper")


def find_relevant_ir_links(html: str, base_url: str) -> List[str]:
    """Finds all links in the IR page matching keywords: event, webcast, conference call, results, news."""
    soup = BeautifulSoup(html, "html.parser")
    found_urls = []
    base_domain = urlparse(base_url).netloc.lower()

    for a in soup.find_all(["a", "iframe"], href=True):
        href = a.get("href") or a.get("src") or ""
        link_text = a.get_text(strip=True).lower()
        href_lower = href.lower()

        # Match keywords
        if any(kw in href_lower or kw in link_text for kw in ["event", "webcast", "conference-call", "conference_call", "earnings", "results", "news", "press"]):
            # Filter out non-event files or non-web pages
            if href_lower.endswith((".pdf", ".zip", ".jpg", ".png", ".svg")):
                continue
            full_url = urljoin(base_url, href)
            # Only follow same root domain or known vendor domains
            target_domain = urlparse(full_url).netloc.lower()
            if base_domain in target_domain or any(v in target_domain for v in ["q4inc.com", "notified.com", "on24.com", "choruscall.com", "webcaster"]):
                if full_url not in found_urls:
                    found_urls.append(full_url)

    return found_urls[:8]


def scrape_ir_event_page(ir_url: str, ticker: str) -> Dict[str, Any]:
    """Scrapes company IR page and follows internal links to discover quarterly earnings calls."""
    result = {
        "ticker": ticker,
        "ir_url": ir_url,
        "vendor": "In-house",
        "webcast_url": None,
        "call_datetime_utc": None,
        "timezone_as_published": None,
        "fiscal_period": None,
        "dial_in_available": None,
        "registration_required": None,
        "replay_url": None,
        "replay_expiry_date": None,
        "announced_at_utc": None,
        "lead_time_hours": None,
        "discovery_source": "IR_EVENTS_PAGE",
        "confidence": 0.60,
    }

    try:
        resp = polite_get(ir_url)
        if resp.status_code != 200:
            logger.warning(f"IR page {ir_url} returned status {resp.status_code}")
            return result

        pages_to_check = [(ir_url, resp.text)]
        child_links = find_relevant_ir_links(resp.text, ir_url)
        
        for link in child_links:
            try:
                c_resp = polite_get(link)
                if c_resp.status_code == 200:
                    pages_to_check.append((link, c_resp.text))
            except Exception:
                pass

        for page_url, html_content in pages_to_check:
            soup = BeautifulSoup(html_content, "html.parser")
            text = soup.get_text(separator=" ", strip=True)

            if is_non_earnings_event(text):
                continue

            # Classify vendor
            vendor, conf = classify_vendor_from_html(html_content, base_url=page_url)
            if vendor and vendor != "In-house":
                result["vendor"] = vendor
                result["confidence"] = conf

            # Check for webcast URL
            for a in soup.find_all(["a", "iframe"], href=True):
                href = a.get("href") or a.get("src") or ""
                if any(kw in href.lower() for kw in ["q4inc", "notified", "on24", "choruscall", "webcaster", "viavid", "audio", "webcast"]):
                    full_href = urljoin(page_url, href)
                    result["webcast_url"] = full_href
                    result["replay_url"] = full_href
                    break

            # Extract fiscal period
            fp = extract_fiscal_period_from_text(text)
            if fp and not result["fiscal_period"]:
                result["fiscal_period"] = fp

            # Extract call date & time
            today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
            call_utc, tz_clean, ann_utc = extract_call_datetime_from_text(text, today_str, None)
            if call_utc and not result["call_datetime_utc"]:
                result["call_datetime_utc"] = call_utc
                result["timezone_as_published"] = tz_clean
                result["announced_at_utc"] = ann_utc
                result["confidence"] = 0.90 if result["fiscal_period"] else 0.75
                break

    except Exception as e:
        logger.warning(f"Error scraping IR for {ticker} ({ir_url}): {e}")

    return result


def extract_canadian_ir_details(ir_url: str, ticker: str) -> Dict[str, Any]:
    """Compatibility alias for scraping Canadian and US IR pages."""
    return scrape_ir_event_page(ir_url, ticker)
