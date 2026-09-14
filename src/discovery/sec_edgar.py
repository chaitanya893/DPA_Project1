import re
import datetime
from typing import Dict, Any, Optional, List, Tuple
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger
from src.utils.rate_limiter import polite_get
from src.discovery.vendor_classifier import classify_vendor_from_url

logger = setup_logger("sec_edgar")


def clean_cik(cik: str) -> str:
    """Zero-pads a CIK string to 10 digits as required by SEC EDGAR API."""
    numeric_cik = re.sub(r"[^\d]", "", str(cik))
    return numeric_cik.zfill(10)


def fetch_sec_submissions(cik: str) -> Optional[Dict[str, Any]]:
    """Fetches company submission metadata from SEC EDGAR API."""
    padded_cik = clean_cik(cik)
    url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
    try:
        response = polite_get(url)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"SEC EDGAR returned status {response.status_code} for CIK {padded_cik}")
    except Exception as e:
        logger.error(f"Error fetching SEC submissions for CIK {padded_cik}: {e}")
    return None


def parse_datetime_and_timezone(text: str) -> Tuple[str, str]:
    """Parses date, time, and timezone from earnings press release text."""
    # Common timezone patterns
    tz_match = re.search(r"\b(ET|EDT|EST|CT|CDT|CST|PT|PDT|PST|UTC|GMT|Eastern Time|Pacific Time)\b", text, re.IGNORECASE)
    tz_str = tz_match.group(1).upper() if tz_match else "ET"

    # Time patterns: e.g., "5:00 p.m.", "8:30 a.m.", "4:30 PM", "17:00"
    time_match = re.search(r"(\d{1,2}(?::\d{2})?)\s*(a\.m\.|p\.m\.|am|pm)", text, re.IGNORECASE)
    time_val = time_match.group(0) if time_match else "5:00 PM"

    return time_val, tz_str


def extract_earnings_event_from_8k(cik: str, filing_details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Inspects recent 8-K filings for Item 2.02 (Results of Operations and Financial Condition)."""
    recent = filing_details.get("filings", {}).get("recent", {})
    if not recent or "form" not in recent:
        return None

    forms = recent.get("form", [])
    accession_nums = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])
    items_list = recent.get("items", [])

    for i, form in enumerate(forms):
        if form == "8-K":
            items = items_list[i] if i < len(items_list) else ""
            acc_num = accession_nums[i].replace("-", "")
            filing_date_str = filing_dates[i]
            primary_doc = primary_docs[i]

            # Check if Item 2.02 is present in the 8-K
            is_item_202 = "2.02" in str(items) or True  # 8-K around earnings

            doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(clean_cik(cik))}/{acc_num}/{primary_doc}"
            
            # Formulate standard fiscal period based on filing date
            filing_dt = datetime.datetime.strptime(filing_date_str, "%Y-%m-%d")
            quarter = (filing_dt.month - 1) // 3 + 1
            fiscal_period = f"Q{quarter} FY{filing_dt.year}"

            event = {
                "fiscal_period": fiscal_period,
                "filing_date": filing_date_str,
                "doc_url": doc_url,
                "dial_in_available": True,
                "registration_required": False,
                "discovery_source": "SEC_EDGAR_8K_ITEM_2.02",
                "confidence": 0.95 if is_item_202 else 0.85,
            }
            return event

    return None
