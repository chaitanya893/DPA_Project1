import datetime
import re
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

TZ_LOOKUP = {
    "ET": "America/New_York",
    "EDT": "America/New_York",
    "EST": "America/New_York",
    "EASTERN TIME": "America/New_York",
    "EASTERN": "America/New_York",
    "U.S. EASTERN TIME": "America/New_York",
    "US EASTERN TIME": "America/New_York",
    "CT": "America/Chicago",
    "CDT": "America/Chicago",
    "CST": "America/Chicago",
    "CENTRAL TIME": "America/Chicago",
    "CENTRAL": "America/Chicago",
    "U.S. CENTRAL TIME": "America/Chicago",
    "MT": "America/Denver",
    "MDT": "America/Denver",
    "MST": "America/Denver",
    "MOUNTAIN TIME": "America/Denver",
    "MOUNTAIN": "America/Denver",
    "PT": "America/Los_Angeles",
    "PDT": "America/Los_Angeles",
    "PST": "America/Los_Angeles",
    "PACIFIC TIME": "America/Los_Angeles",
    "PACIFIC": "America/Los_Angeles",
    "U.S. PACIFIC TIME": "America/Los_Angeles",
    "UTC": "UTC",
    "GMT": "UTC",
}


def clean_timezone_str(tz_raw: Optional[str]) -> Optional[str]:
    """Cleans raw timezone string and maps to standardized key."""
    if not tz_raw:
        return None
    cleaned = re.sub(r"[\(\)\[\]]", "", tz_raw).strip().upper()
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Handle dual tz like "1:30 PM PT / 4:30 PM ET"
    if "/" in cleaned:
        parts = [p.strip() for p in cleaned.split("/")]
        for p in parts:
            if p in TZ_LOOKUP:
                return p
    if cleaned in TZ_LOOKUP:
        return cleaned
    for k in TZ_LOOKUP:
        if k in cleaned:
            return k
    return None


def parse_call_datetime_to_utc(
    date_str: Optional[str],
    time_str: Optional[str] = None,
    tz_str: Optional[str] = None
) -> Tuple[Optional[datetime.datetime], Optional[str]]:
    """Parses date string, time string, and timezone into a timezone-aware UTC datetime.
    
    If time or timezone cannot be determined from text, returns (None, None) or partial without guessing.
    """
    if not date_str:
        return None, None

    date_str_clean = date_str.strip().rstrip(".,")
    clean_tz = clean_timezone_str(tz_str)
    iana_tz_name = TZ_LOOKUP.get(clean_tz) if clean_tz else None

    # Parse time if provided
    hour: Optional[int] = None
    minute: Optional[int] = None

    if time_str:
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(a\.m\.|p\.m\.|am|pm)?", time_str, re.IGNORECASE)
        if time_match:
            h = int(time_match.group(1))
            m = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = (time_match.group(3) or "").lower().replace(".", "")
            if ampm == "pm" and h < 12:
                h += 12
            elif ampm == "am" and h == 12:
                h = 0
            hour = h
            minute = m

    # If no timezone or no time was discovered, we cannot accurately compute UTC datetime
    if hour is None or iana_tz_name is None:
        return None, clean_tz

    tz = ZoneInfo(iana_tz_name)

    # Try standard date formats
    dt_obj = None
    for fmt in ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%Y-%m-%d", "%m/%d/%Y", "%d %B %Y", "%d %b %Y"]:
        try:
            parsed_d = datetime.datetime.strptime(date_str_clean, fmt)
            dt_obj = parsed_d.replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=tz)
            break
        except ValueError:
            continue

    if dt_obj is None:
        return None, clean_tz

    utc_dt = dt_obj.astimezone(ZoneInfo("UTC"))
    return utc_dt, clean_tz
