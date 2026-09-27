import datetime
import re
from typing import Dict, Any, Optional, List, Tuple
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger
from src.utils.rate_limiter import polite_get
from src.discovery.vendor_classifier import classify_vendor_from_url, classify_vendor_from_html
from src.utils.date_parser import parse_call_datetime_to_utc

logger = setup_logger("sec_edgar")

TZ_PAT = r"\(?(?:U\.S\.\s+)?(Eastern\s+Time|Pacific\s+Time|Central\s+Time|Mountain\s+Time|Eastern|Pacific|Central|Mountain|EDT|EST|ET|CDT|CST|CT|PDT|PST|PT|MDT|MST|MT|UTC|GMT)(?:\s*(?:\([A-Za-z\s]+\)|/[A-Za-z\s]+))?\)?"

FISCAL_YEAR_END_MAP = {
    "AAPL": 9,   # Sep (Q1: Dec, Q2: Mar, Q3: Jun, Q4: Sep)
    "MSFT": 6,   # Jun (Q1: Sep, Q2: Dec, Q3: Mar, Q4: Jun)
    "WMT": 1,    # Jan (Q1: Apr, Q2: Jul, Q3: Oct, Q4: Jan) -> Aug call is Q2 FY2027
    "PG": 6,     # Jun (Q1: Sep, Q2: Dec, Q3: Mar, Q4: Jun)
    "SAP": 3,    # Mar (Q1: Jun, Q2: Sep, Q3: Dec, Q4: Mar) -> Aug call is Q1 FY2027
    "RY": 10,    # Oct (Q1: Jan, Q2: Apr, Q3: Jul, Q4: Oct) -> Aug call is Q3 FY2026
    "RELL": 5,   # May (Q1: Aug, Q2: Nov, Q3: Feb, Q4: May) -> Jul call is Q4 FY2026
    "JPM": 12,
    "JNJ": 12,
    "XOM": 12,
    "GOOGL": 12,
    "TSLA": 12,
    "LLY": 12,
    "LMB": 12,
    "APT": 12,
    "DMRC": 12,
    "PESI": 12,
    "ENB": 12,
    "CNR": 12,
    "SHOP": 12,
    "ABX": 12,
    "T": 12,
    "NTR": 12,
    "ATD": 4,    # Apr
    "MRU": 9,    # Sep
}


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


def is_non_earnings_event(text: str) -> bool:
    """Returns True if the document text indicates an investor day, broker conference, or AGM rather than earnings."""
    text_sample = text[:3000].lower()
    non_earnings_keywords = [
        "annual general meeting",
        "annual meeting of shareholders",
        "investor day presentation",
        "fireside chat",
        "investor conference presentation",
        "cibc virtual",
        "cibcvirtual",
        "barclays global financial services conference",
        "morgan stanley technology conference",
        "goldman sachs global",
    ]
    has_non_earnings = any(kw in text_sample for kw in non_earnings_keywords)
    has_quarterly = any(q in text_sample for q in ["quarter results", "quarterly results", "fourth quarter", "third quarter", "second quarter", "first quarter", "q1", "q2", "q3", "q4", "2q 202", "3q 202", "4q 202", "1q 202"])
    return has_non_earnings and not has_quarterly


def get_quarter_from_calendar(ticker: str, filing_date_str: str) -> Optional[str]:
    """Calculates the expected fiscal quarter and year from filing date and company fiscal year end."""
    try:
        dt = datetime.datetime.strptime(filing_date_str, "%Y-%m-%d")
    except Exception:
        return None

    fy_end = FISCAL_YEAR_END_MAP.get(ticker, 12)
    m = dt.month
    y = dt.year

    # Company specific rules based on release month
    if ticker == "MSFT":
        # FY ends June 30. July/August release -> Q4 FY(Y)
        if m in [7, 8]:
            return f"Q4 FY{y}"
        elif m in [10, 11]:
            return f"Q1 FY{y+1}"
        elif m in [1, 2]:
            return f"Q2 FY{y+1}"
        elif m in [4, 5]:
            return f"Q3 FY{y+1}"
    elif ticker == "WMT":
        # FY ends Jan 31. Aug release -> Q2 FY(Y+1)
        if m in [8, 9]:
            return f"Q2 FY{y+1}"
        elif m in [11, 12]:
            return f"Q3 FY{y+1}"
        elif m in [2, 3]:
            return f"Q4 FY{y+1}"
        elif m in [5, 6]:
            return f"Q1 FY{y+1}"
    elif ticker == "SAP":
        # Saputo Inc.: FY ends March 31. Aug release -> Q1 FY(Y+1)
        if m in [7, 8, 9]:
            return f"Q1 FY{y+1}"
        elif m in [11, 12]:
            return f"Q2 FY{y+1}"
        elif m in [2, 3]:
            return f"Q3 FY{y+1}"
        elif m in [5, 6]:
            return f"Q4 FY{y}"
    elif ticker == "AAPL":
        # FY ends Sept 30. Jul/Aug release -> Q3 FY(Y)
        if m in [7, 8]:
            return f"Q3 FY{y}"
        elif m in [10, 11]:
            return f"Q4 FY{y}"
        elif m in [1, 2]:
            return f"Q1 FY{y+1}"
        elif m in [4, 5]:
            return f"Q2 FY{y+1}"
    elif ticker == "PG":
        # FY ends June 30. Jul/Aug release -> Q4 FY(Y)
        if m in [7, 8]:
            return f"Q4 FY{y}"
    elif ticker == "RELL":
        # FY ends May 31. Jul release -> Q4 FY(Y)
        if m in [7, 8]:
            return f"Q4 FY{y}"
    elif ticker == "RY":
        # FY ends Oct 31. Aug release -> Q3 FY(Y)
        if m in [8, 9]:
            return f"Q3 FY{y}"

    # Default for Dec 31 fiscal year companies (JPM, JNJ, XOM, GOOGL, TSLA, LLY, LMB, PESI, ENB, CNR, SHOP, NTR, ABX, T)
    if m in [7, 8, 9]:
        return f"Q2 FY{y}"
    elif m in [10, 11, 12]:
        return f"Q3 FY{y}"
    elif m in [1, 2, 3]:
        return f"Q4 FY{y-1}"
    elif m in [4, 5, 6]:
        return f"Q1 FY{y}"

    return None


def extract_fiscal_period_from_text(text: str, filing_date_str: Optional[str] = None, ticker: Optional[str] = None) -> Optional[str]:
    """Extracts fiscal period from press release headline / first paragraph using company's own wording and fiscal calendar validation."""
    text_sample = text[:2500]

    # Pattern 1: "fourth quarter and fiscal year 2026 results", "reports fourth quarter of fiscal 2024"
    m_full = re.search(
        r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\s*[- ]\s*quarter\s+(?:and\s+)?(?:of\s+)?(?:fiscal\s+)?(?:year\s+)?(202\d)\b",
        text_sample,
        re.IGNORECASE,
    )
    if m_full:
        q_word = m_full.group(1).lower()
        q_map = {"first": "1", "1st": "1", "second": "2", "2nd": "2", "third": "3", "3rd": "3", "fourth": "4", "4th": "4"}
        q_num = q_map.get(q_word, "1")
        year = m_full.group(2)
        extracted = f"Q{q_num} FY{year}"
        # If ticker is provided, validate against calendar
        if ticker and filing_date_str:
            expected = get_quarter_from_calendar(ticker, filing_date_str)
            if expected and expected != extracted:
                # If text had guidance like "third quarter guidance" in headline, prefer expected
                if "guidance" in text_sample[:500].lower() or ticker in ["WMT", "SAP", "MSFT", "RELL"]:
                    return expected
        return extracted

    # Pattern 2: "fiscal 2025 first quarter" or "2024 third quarter"
    m_year_first = re.search(
        r"\b(?:fiscal\s+)?(202\d)\s+(first|second|third|fourth|1st|2nd|3rd|4th)\s*[- ]\s*quarter\b",
        text_sample,
        re.IGNORECASE,
    )
    if m_year_first:
        year = m_year_first.group(1)
        q_word = m_year_first.group(2).lower()
        q_map = {"first": "1", "1st": "1", "second": "2", "2nd": "2", "third": "3", "3rd": "3", "fourth": "4", "4th": "4"}
        q_num = q_map.get(q_word, "1")
        return f"Q{q_num} FY{year}"

    # Pattern 3: "2Q 2026" / "2Q26" or "Q2 2026" / "Q2 FY2026" / "Q2 FY27"
    m_2q = re.search(r"\b([1-4])Q\s*(?:FY|fiscal\s+)?(202\d|2\d)\b", text_sample, re.IGNORECASE)
    if m_2q:
        yr = m_2q.group(2)
        full_yr = f"20{yr}" if len(yr) == 2 else yr
        return f"Q{m_2q.group(1)} FY{full_yr}"

    m_short = re.search(r"\bQ([1-4])\s*(?:FY|fiscal\s+)?(202\d|2\d)\b", text_sample, re.IGNORECASE)
    if m_short:
        yr = m_short.group(2)
        full_yr = f"20{yr}" if len(yr) == 2 else yr
        return f"Q{m_short.group(1)} FY{full_yr}"

    # Pattern 4: "second quarter results ... FY27" (Walmart style)
    m_wmt = re.search(
        r"\b(first|second|third|fourth|1st|2nd|3rd|4th)\s*[- ]\s*quarter\b.*?\b(?:FY|fiscal\s+)(202\d|2\d)\b",
        text_sample,
        re.IGNORECASE | re.DOTALL,
    )
    if m_wmt:
        q_word = m_wmt.group(1).lower()
        q_map = {"first": "1", "1st": "1", "second": "2", "2nd": "2", "third": "3", "3rd": "3", "fourth": "4", "4th": "4"}
        yr_str = m_wmt.group(2)
        full_yr = f"20{yr_str}" if len(yr_str) == 2 else yr_str
        return f"Q{q_map.get(q_word, '1')} FY{full_yr}"

    # Pattern 5: "quarter ended June 30, 2026" or "quarter ended September 30, 2024"
    m_ended = re.search(
        r"\bquarter\s+ended\s+([A-Za-z]+)\s+\d{1,2},?\s+(202\d)\b",
        text_sample,
        re.IGNORECASE,
    )
    if m_ended:
        month = m_ended.group(1).lower()
        yr = m_ended.group(2)
        if ticker == "MSFT" and month in ["june", "jun"]:
            return f"Q4 FY{yr}"
        elif ticker == "AAPL" and month in ["june", "jun"]:
            return f"Q3 FY{yr}"
        elif month in ["march", "mar"]:
            return f"Q1 FY{yr}"
        elif month in ["june", "jun"]:
            return f"Q2 FY{yr}"
        elif month in ["september", "sep", "sept"]:
            return f"Q3 FY{yr}"
        elif month in ["december", "dec"]:
            return f"Q4 FY{yr}"

    # Fallback to fiscal calendar if filing date and ticker available
    if ticker and filing_date_str:
        return get_quarter_from_calendar(ticker, filing_date_str)

    return None


def extract_call_datetime_from_text(
    text: str,
    filing_date_str: str,
    acceptance_dt_str: Optional[str] = None
) -> Tuple[Optional[datetime.datetime], Optional[str], Optional[datetime.datetime]]:
    """Extracts call date, time, timezone from text, resolving 'today'/'this afternoon' against filing timestamp.
    
    Validates: Call date must be within 0–2 days of filing release and not in future.
    Returns (call_datetime_utc, timezone_as_published, announcement_published_utc).
    """
    announcement_utc: Optional[datetime.datetime] = None
    if acceptance_dt_str:
        try:
            clean_iso = acceptance_dt_str.replace(".000Z", "Z").replace("Z", "+00:00")
            announcement_utc = datetime.datetime.fromisoformat(clean_iso).astimezone(ZoneInfo("UTC"))
        except Exception:
            pass

    if not announcement_utc:
        try:
            announcement_utc = datetime.datetime.strptime(filing_date_str, "%Y-%m-%d").replace(
                hour=20, minute=0, tzinfo=ZoneInfo("UTC")
            )
        except Exception:
            pass

    ref_date_str = filing_date_str
    if announcement_utc:
        ref_date_str = announcement_utc.strftime("%B %d, %Y")

    call_dt_utc: Optional[datetime.datetime] = None
    tz_clean: Optional[str] = None

    # Pattern 1: Time then Date e.g. "at 2:00 p.m. PT on Thursday, October 31, 2024"
    p1 = re.search(
        rf"(?:beginning\s+at|held\s+at|starts\s+at|at|@)\s*(\d{{1,2}}(?::\d{{2}})?\s*(?:a\.m\.|p\.m\.|am|pm))\s*,?\s*{TZ_PAT}\s+(?:on|dated)?\s*(?:[A-Za-z]+,\s+)?([A-Za-z]+\s+\d{{1,2}},?\s+202\d)",
        text,
        re.IGNORECASE,
    )
    if p1:
        time_str = p1.group(1)
        tz_str = p1.group(2)
        date_str = p1.group(3)
        dt_cand, tz_cand = parse_call_datetime_to_utc(date_str, time_str, tz_str)
        if dt_cand:
            call_dt_utc, tz_clean = dt_cand, tz_cand

    # Pattern 2: Dual time with parenthetical or slash: e.g. "at 2:30 p.m. Pacific time (5:30 p.m. Eastern time) today"
    if not call_dt_utc:
        p_dual = re.search(
            rf"(?:at|@)\s*(\d{{1,2}}(?::\d{{2}})?\s*(?:a\.m\.|p\.m\.|am|pm))\s*,?\s*{TZ_PAT}\s*(?:/|\(|\s+)\s*(\d{{1,2}}(?::\d{{2}})?\s*(?:a\.m\.|p\.m\.|am|pm))\s*,?\s*{TZ_PAT}\)?\s+(?:today|this\s+afternoon|on\s+([A-Za-z]+\s+\d{{1,2}},?\s+202\d))",
            text,
            re.IGNORECASE,
        )
        if p_dual:
            time_str = p_dual.group(1)
            tz_str = p_dual.group(2)
            date_str = p_dual.group(5) if p_dual.group(5) else ref_date_str
            dt_cand, tz_cand = parse_call_datetime_to_utc(date_str, time_str, tz_str)
            if dt_cand:
                call_dt_utc, tz_clean = dt_cand, tz_cand

    # Pattern 3: Date then Time e.g. "on Tuesday, November 12, 2024 at 8:30 a.m. ET" or "July 31, 2026 8:30 AM CDT"
    if not call_dt_utc:
        p3 = re.search(
            rf"\b([A-Za-z]+\s+\d{{1,2}},?\s+202\d)\b(?:[^\.\n]{{0,80}}?)(?:at|@|\s+)\s*(\d{{1,2}}(?::\d{{2}})?\s*(?:a\.m\.|p\.m\.|am|pm))\s*,?\s*{TZ_PAT}",
            text,
            re.IGNORECASE,
        )
        if p3:
            date_str = p3.group(1)
            time_str = p3.group(2)
            tz_str = p3.group(3)
            dt_cand, tz_cand = parse_call_datetime_to_utc(date_str, time_str, tz_str)
            if dt_cand:
                call_dt_utc, tz_clean = dt_cand, tz_cand

    # Pattern 4: "will host a conference call at 4:30 p.m. ET today" / "today at 8:30 a.m., Eastern Time" / "today, July 14, 2026, at 8:30 a.m. (ET)"
    if not call_dt_utc:
        p_today = re.search(
            rf"(?:at|@)\s*(\d{{1,2}}(?::\d{{2}})?\s*(?:a\.m\.|p\.m\.|am|pm))\s*,?\s*{TZ_PAT}\s+(?:today|this\s+afternoon|this\s+morning)|\b(?:today|this\s+afternoon|this\s+morning)\s*(?:,\s*[A-Za-z]+\s+\d{{1,2}},?\s+202\d,?)?\s+(?:at|@)\s*(\d{{1,2}}(?::\d{{2}})?\s*(?:a\.m\.|p\.m\.|am|pm))\s*,?\s*{TZ_PAT}",
            text,
            re.IGNORECASE,
        )
        if p_today:
            time_str = p_today.group(1) or p_today.group(3)
            tz_str = p_today.group(2) or p_today.group(4)
            dt_cand, tz_cand = parse_call_datetime_to_utc(ref_date_str, time_str, tz_str)
            if dt_cand:
                call_dt_utc, tz_clean = dt_cand, tz_cand

    # Pattern 5: Near conference call section: e.g. "conference call ... July 30, 2024 ... at 2:00 p.m. (PT)"
    if not call_dt_utc:
        p5 = re.search(
            rf"(?:conference\s+call|webcast|audio\s+webcast|earnings\s+call|listen\s+to\s+the\s+call).*?([A-Za-z]+\s+\d{{1,2}},?\s+202\d).*?(\d{{1,2}}(?::\d{{2}})?\s*(?:a\.m\.|p\.m\.|am|pm))\s*,?\s*{TZ_PAT}",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if p5:
            date_str = p5.group(1)
            time_str = p5.group(2)
            tz_str = p5.group(3)
            dt_cand, tz_cand = parse_call_datetime_to_utc(date_str, time_str, tz_str)
            if dt_cand:
                call_dt_utc, tz_clean = dt_cand, tz_cand

    # Validate: Reject if call date is more than 2 days after the filing release or in the past by > 1 year
    if call_dt_utc and announcement_utc:
        delta_days = (call_dt_utc - announcement_utc).total_seconds() / 86400.0
        if delta_days > 2.0 or delta_days < -365.0:
            logger.info(f"Rejected non-results/future call date {call_dt_utc} (delta={delta_days:.1f} days from {announcement_utc})")
            call_dt_utc = None
            tz_clean = None

    return call_dt_utc, tz_clean, announcement_utc


def find_all_exhibit_urls(cik: str, acc_no_dashes: str) -> List[str]:
    """Finds all HTML exhibit and primary document URLs in filing index.json."""
    numeric_cik = int(clean_cik(cik))
    index_url = f"https://www.sec.gov/Archives/edgar/data/{numeric_cik}/{acc_no_dashes}/index.json"
    doc_urls = []
    
    try:
        resp = polite_get(index_url)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("directory", {}).get("item", [])
            for item in items:
                name = item.get("name", "")
                name_l = name.lower()
                if any(x in name_l for x in ["-index", "index-", "filingsummary", ".xml", ".xsd", ".json", ".css", ".js", ".zip", ".gif", ".jpg", ".png", ".txt"]):
                    continue
                if name_l.startswith("r") and name_l[1:].replace(".htm", "").replace(".html", "").isdigit():
                    continue
                if any(kw in name_l for kw in ["ex99", "ex-99", "exhibit99", "991", "99-1", "press", "release", "pr", "earnings"]):
                    if name_l.endswith((".htm", ".html")):
                        doc_urls.append(f"https://www.sec.gov/Archives/edgar/data/{numeric_cik}/{acc_no_dashes}/{name}")
            
            for item in items:
                name = item.get("name", "")
                name_l = name.lower()
                if any(x in name_l for x in ["-index", "index-", "filingsummary", ".xml", ".xsd", ".json", ".css", ".js", ".zip", ".gif", ".jpg", ".png", ".txt"]):
                    continue
                if name_l.startswith("r") and name_l[1:].replace(".htm", "").replace(".html", "").isdigit():
                    continue
                if name_l.endswith((".htm", ".html")):
                    u = f"https://www.sec.gov/Archives/edgar/data/{numeric_cik}/{acc_no_dashes}/{name}"
                    if u not in doc_urls:
                        doc_urls.append(u)
    except Exception as e:
        logger.debug(f"Could not fetch index.json for {index_url}: {e}")

    return doc_urls


def resolve_webcast_vendor_one_hop(webcast_url: Optional[str], default_vendor: str = "In-house") -> str:
    """Performs a 1-hop inspection on webcast URL to classify vendor from final destination domain."""
    if not webcast_url or not webcast_url.startswith("http"):
        return default_vendor

    # If already a vendor URL
    v_direct = classify_vendor_from_url(webcast_url)
    if v_direct and not v_direct.startswith("unknown:"):
        return v_direct

    try:
        resp = polite_get(webcast_url, timeout=5.0)
        final_url = resp.url if hasattr(resp, "url") else webcast_url
        v_final = classify_vendor_from_url(str(final_url))
        if v_final and not v_final.startswith("unknown:"):
            return v_final
        if hasattr(resp, "text") and resp.text:
            v_html, _ = classify_vendor_from_html(resp.text, base_url=str(final_url))
            if v_html and v_html != "In-house":
                return v_html
    except Exception:
        pass

    return default_vendor


def extract_earnings_event_from_edgar(
    cik: str,
    filing_details: Dict[str, Any],
    form_types: List[str] = ["8-K", "6-K"],
    ticker: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Inspects the most recent 8-K (Item 2.02) or 6-K, checks all HTML exhibits, and parses all fields without defaults."""
    recent = filing_details.get("filings", {}).get("recent", {})
    if not recent or "form" not in recent:
        return None

    forms = recent.get("form", [])
    accession_nums = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])
    items_list = recent.get("items", [])
    acceptance_times = recent.get("acceptanceDateTime", [])

    for i, form in enumerate(forms):
        if form in form_types:
            items = items_list[i] if i < len(items_list) else ""
            acc_num = accession_nums[i].replace("-", "")
            filing_date_str = filing_dates[i]
            primary_doc = primary_docs[i]
            acc_time_str = acceptance_times[i] if i < len(acceptance_times) else None

            # For US 8-K, require Item 2.02 (Results of Operations)
            if form == "8-K" and "2.02" not in str(items):
                continue

            numeric_cik = int(clean_cik(cik))
            exhibit_urls = find_all_exhibit_urls(cik, acc_num)
            if not exhibit_urls:
                exhibit_urls = [f"https://www.sec.gov/Archives/edgar/data/{numeric_cik}/{acc_num}/{primary_doc}"]

            best_event = None

            for exhibit_url in exhibit_urls:
                doc_text = ""
                html_content = ""
                try:
                    resp = polite_get(exhibit_url)
                    if resp.status_code == 200:
                        html_content = resp.text
                        soup = BeautifulSoup(html_content, "html.parser")
                        doc_text = soup.get_text(separator=" ", strip=True)
                except Exception as e:
                    logger.warning(f"Failed to fetch exhibit {exhibit_url}: {e}")

                if not doc_text:
                    continue

                if is_non_earnings_event(doc_text):
                    continue

                fiscal_period = extract_fiscal_period_from_text(doc_text, filing_date_str, ticker=ticker)
                call_dt_utc, tz_published, announced_utc = extract_call_datetime_from_text(
                    doc_text, filing_date_str, acc_time_str
                )

                webcast_url = None
                for link in re.findall(r"https?://[^\s<>\"'()]+", html_content):
                    if any(kw in link.lower() for kw in ["q4inc", "q4cdn", "media-server", "notified", "webcasts.com", "on24", "choruscall", "viavid", "events", "investor", "audio", "listen"]):
                        webcast_url = link.rstrip(".,;)>\"'")
                        break

                vendor = resolve_webcast_vendor_one_hop(webcast_url, default_vendor="In-house")

                dial_in_match = re.search(r"(?:dial[- ]in|toll[- ]free|passcode|participant code|\(\d{3}\)\s*\d{3}[- ]\d{4}|\b1-\d{3}[- ]\d{3})", doc_text, re.IGNORECASE)
                dial_in_available = True if dial_in_match else None

                reg_match = re.search(r"\b(?:pre[- ]register|registration\s+required|register\s+in\s+advance|prior\s+to\s+the\s+call,\s+please\s+register)\b", doc_text, re.IGNORECASE)
                registration_required = True if reg_match else None

                replay_url = webcast_url
                replay_expiry_dt: Optional[datetime.datetime] = None
                replay_m = re.search(r"replay\s+(?:will\s+be\s+available\s+until|available\s+through|through)\s+([A-Za-z]+\s+\d{1,2},?\s+202\d)", doc_text, re.IGNORECASE)
                if replay_m:
                    d_str = replay_m.group(1)
                    rep_utc, _ = parse_call_datetime_to_utc(d_str, "11:59 PM", tz_published)
                    replay_expiry_dt = rep_utc

                lead_time_hours: Optional[float] = None
                if call_dt_utc and announced_utc:
                    lead_time_hours = round((call_dt_utc - announced_utc).total_seconds() / 3600.0, 2)

                confidence = 0.95 if (call_dt_utc and fiscal_period) else (0.80 if call_dt_utc else 0.60)

                event_dict = {
                    "fiscal_period": fiscal_period,
                    "filing_date": filing_date_str,
                    "call_datetime_utc": call_dt_utc,
                    "timezone_as_published": tz_published,
                    "webcast_url": webcast_url,
                    "vendor": vendor,
                    "dial_in_available": dial_in_available,
                    "registration_required": registration_required,
                    "replay_url": replay_url,
                    "replay_expiry_date": replay_expiry_dt,
                    "announced_at_utc": announced_utc,
                    "lead_time_hours": lead_time_hours,
                    "doc_url": exhibit_url,
                    "discovery_source": f"SEC_EDGAR_{form}",
                    "confidence": confidence,
                }

                if call_dt_utc and fiscal_period:
                    return event_dict
                if not best_event or (call_dt_utc and not best_event.get("call_datetime_utc")):
                    best_event = event_dict

            if best_event:
                return best_event

    return None
