import re
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger

logger = setup_logger("vendor_classifier")

# Webcast Vendor Pattern Registry
VENDOR_PATTERNS: Dict[str, Dict[str, list]] = {
    "Q4 Inc": {
        "url_regex": [
            r"events\.q4inc\.com",
            r"q4cdn\.com",
            r"q4web\.com",
            r"q4app\.com",
            r"api\.q4websystems\.com",
            r"q4investor\.com",
        ],
        "html_signatures": [
            "q4-app",
            "q4widgets",
            "q4inc",
            "q4-event-details",
            "Q4.WebSystems",
        ],
    },
    "Notified": {
        "url_regex": [
            r"event\.notified\.com",
            r"webcasts\.eqr\.com",
            r"notified\.com",
            r"west-master\.com",
            r"broadcast-teleconference\.com",
            r"globestats\.com",
        ],
        "html_signatures": [
            "notified-webcast",
            "intrado",
            "notified.com",
            "west-master",
        ],
    },
    "Nasdaq IR": {
        "url_regex": [
            r"services\.choruscall\.com",
            r"choruscall\.com",
            r"nasdaq\.com/ir",
            r"nasdaqomx",
            r"viavid\.webcasts\.com",
        ],
        "html_signatures": [
            "choruscall",
            "nasdaq-ir",
            "viavid",
        ],
    },
    "Investis": {
        "url_regex": [
            r"investis\.com",
            r"investisdigital\.com",
        ],
        "html_signatures": [
            "investis-module",
            "investisdigital",
        ],
    },
    "ON24": {
        "url_regex": [
            r"event\.on24\.com",
            r"on24\.com",
        ],
        "html_signatures": [
            "on24",
            "wcc/r/",
        ],
    },
    "Zoom Events": {
        "url_regex": [
            r"zoom\.us/j/",
            r"zoom\.us/webinar",
            r"events\.zoom\.us",
        ],
        "html_signatures": [
            "zoom.us/webinar",
            "zoom-event",
        ],
    },
    "Kaltura": {
        "url_regex": [
            r"kaltura\.com",
            r"cdnapisec\.kaltura\.com",
        ],
        "html_signatures": [
            "kalturaPlayer",
            "kaltura-logo",
        ],
    },
}


def classify_vendor_from_url(url: str) -> Optional[str]:
    """Determines the IR webcast vendor from a URL string."""
    if not url:
        return None
    for vendor_name, config in VENDOR_PATTERNS.items():
        for pattern in config["url_regex"]:
            if re.search(pattern, url, re.IGNORECASE):
                return vendor_name
    return None


def classify_vendor_from_html(html_content: str, base_url: str = "") -> Tuple[str, float]:
    """Analyzes page HTML and URLs to classify the webcast platform and assign a confidence score."""
    # 1. First check URL patterns in base_url
    url_vendor = classify_vendor_from_url(base_url)
    if url_vendor:
        return url_vendor, 0.95

    # 2. Check iframe and script links in HTML
    if not html_content:
        return "Custom / In-House", 0.50

    soup = BeautifulSoup(html_content, "html.parser")
    
    # Check all iframes and anchor tags
    for elem in soup.find_all(["iframe", "a", "script"]):
        src = elem.get("src") or elem.get("href") or ""
        matched_vendor = classify_vendor_from_url(src)
        if matched_vendor:
            return matched_vendor, 0.90

    # 3. Check text signatures and class names in HTML
    html_lower = html_content.lower()
    for vendor_name, config in VENDOR_PATTERNS.items():
        for sig in config["html_signatures"]:
            if sig.lower() in html_lower:
                return vendor_name, 0.85

    # Fallback to in-house or custom company player
    return "Custom / In-House", 0.60
