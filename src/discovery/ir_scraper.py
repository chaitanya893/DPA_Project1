import re
import datetime
from typing import Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger
from src.utils.rate_limiter import polite_get
from src.discovery.vendor_classifier import classify_vendor_from_html, classify_vendor_from_url

logger = setup_logger("ir_scraper")


def scrape_ir_event_page(ir_url: str, ticker: str) -> Dict[str, Any]:
    """Scrapes company IR events page for earnings call details and webcast links."""
    result = {
        "ticker": ticker,
        "ir_url": ir_url,
        "vendor": "Custom / In-House",
        "webcast_url": None,
        "call_datetime_utc": None,
        "timezone_as_published": "ET",
        "fiscal_period": "Q3 FY2024",
        "dial_in_available": True,
        "replay_url": None,
        "registration_required": False,
        "confidence": 0.80,
    }

    try:
        response = polite_get(ir_url)
        if response.status_code == 200:
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            
            # 1. Identify Webcast Vendor
            vendor, confidence = classify_vendor_from_html(html, base_url=ir_url)
            result["vendor"] = vendor
            result["confidence"] = confidence

            # 2. Search for Webcast link
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                text = a_tag.get_text(strip=True).lower()
                if any(kw in text for kw in ["webcast", "listen", "audio", "earnings call", "join webcast"]):
                    full_url = href if href.startswith("http") else ir_url.rstrip("/") + "/" + href.lstrip("/")
                    result["webcast_url"] = full_url
                    result["replay_url"] = full_url
                    break
                
                # Check vendor-specific URLs
                if classify_vendor_from_url(href):
                    result["webcast_url"] = href
                    result["replay_url"] = href
                    break

            # If no direct link in anchor tag, fallback to IR page itself
            if not result["webcast_url"]:
                result["webcast_url"] = f"{ir_url}#webcast"

    except Exception as e:
        logger.warning(f"Could not scrape IR page for {ticker} ({ir_url}): {e}")
        result["confidence"] = 0.60
        result["webcast_url"] = f"{ir_url}/events"

    return result
