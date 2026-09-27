import os
import json
import time
import hashlib
from pathlib import Path
from typing import Callable, Any, Dict, Optional
from urllib.parse import urlparse
import httpx
from src.utils.logger import setup_logger, get_correlation_id
from config.settings import USER_AGENT, RATE_LIMIT_DELAY, REQUEST_TIMEOUT, BASE_DIR
from src.db.session import SessionLocal
from src.db.models import CrawlLog

logger = setup_logger("rate_limiter")

CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory tracking of last request timestamp per domain
_last_request_time: Dict[str, float] = {}


class CachedResponse:
    """Wrapper mimicking httpx.Response for cached disk content."""
    def __init__(self, status_code: int, text: str, url: str):
        self.status_code = status_code
        self.text = text
        self.url = url

    def json(self) -> Any:
        return json.loads(self.text)


def _get_cache_path(url: str, params: Optional[Dict[str, Any]] = None) -> Path:
    raw_key = f"{url}?{sorted(params.items()) if params else ''}"
    h = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{h}.json"


def log_crawl_to_db(
    url: str,
    status_code: Optional[int],
    duration_ms: int,
    outcome: str,
    error_msg: Optional[str] = None
) -> None:
    """Logs real HTTP request parameters directly into crawl_log table."""
    try:
        db = SessionLocal()
        domain = urlparse(url).netloc
        corr_id = get_correlation_id()
        crawl = CrawlLog(
            source=domain or "HTTP_REQUEST",
            target_url=url,
            http_status=status_code,
            outcome=outcome,
            duration_ms=duration_ms,
            error_message=error_msg,
            correlation_id=corr_id,
        )
        db.add(crawl)
        db.commit()
        db.close()
    except Exception as e:
        logger.debug(f"Could not log crawl to db: {e}")


def polite_get(
    url: str,
    headers: Dict[str, str] = None,
    params: Dict[str, Any] = None,
    max_retries: int = 2,
    backoff_factor: float = 1.5,
    timeout: float = 10.0,
    use_cache: bool = True,
) -> Any:
    """Performs HTTP GET request with disk caching, domain rate limiting, backoff, and DB logging."""
    cache_file = _get_cache_path(url, params)
    
    # 1. Return from disk cache if present
    if use_cache and cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                status = data.get("status_code", 200)
                log_crawl_to_db(url, status, 1, "SUCCESS_CACHED")
                return CachedResponse(status_code=status, text=data.get("text", ""), url=url)
        except Exception:
            pass

    domain = urlparse(url).netloc
    
    # 2. Domain rate limiting enforcement
    now = time.time()
    last_time = _last_request_time.get(domain, 0.0)
    elapsed = now - last_time
    if elapsed < RATE_LIMIT_DELAY:
        sleep_duration = RATE_LIMIT_DELAY - elapsed
        time.sleep(sleep_duration)
    
    _last_request_time[domain] = time.time()

    # 3. Prepare headers
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8"
    }
    if headers:
        request_headers.update(headers)

    # 4. Request loop
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        t0 = time.time()
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, headers=request_headers, params=params)
                duration_ms = int((time.time() - t0) * 1000)
                
                if response.status_code == 429:
                    log_crawl_to_db(url, 429, duration_ms, "BLOCKED", "HTTP 429 Rate Limited")
                    logger.warning(f"Rate limited (429) on {domain}. Backing off for {delay}s (Attempt {attempt}/{max_retries})")
                    time.sleep(delay)
                    delay *= backoff_factor
                    continue
                
                if response.status_code >= 400:
                    outcome = "BLOCKED" if response.status_code in [401, 403] else "FAILED"
                    log_crawl_to_db(url, response.status_code, duration_ms, outcome, f"HTTP {response.status_code}")
                    if response.status_code >= 500:
                        logger.warning(f"Server error ({response.status_code}) on {url}. Backing off {delay}s")
                        time.sleep(delay)
                        delay *= backoff_factor
                        continue
                    return response

                log_crawl_to_db(url, response.status_code, duration_ms, "SUCCESS")

                # Save successful response to disk cache
                if use_cache:
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump({"status_code": response.status_code, "text": response.text}, f)
                    except Exception:
                        pass

                return response

        except (httpx.RequestError, httpx.TimeoutException) as e:
            duration_ms = int((time.time() - t0) * 1000)
            log_crawl_to_db(url, None, duration_ms, "FAILED", str(e))
            logger.warning(f"Network error on {url}: {e}. Retrying in {delay}s (Attempt {attempt}/{max_retries})")
            if attempt == max_retries:
                raise
            time.sleep(delay)
            delay *= backoff_factor

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts.")
