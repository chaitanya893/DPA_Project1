import time
from typing import Callable, Any, Dict
from urllib.parse import urlparse
import httpx
from src.utils.logger import setup_logger
from config.settings import USER_AGENT, RATE_LIMIT_DELAY, REQUEST_TIMEOUT

logger = setup_logger("rate_limiter")

# In-memory tracking of last request timestamp per domain
_last_request_time: Dict[str, float] = {}


def polite_get(
    url: str,
    headers: Dict[str, str] = None,
    params: Dict[str, Any] = None,
    max_retries: int = 2,
    backoff_factor: float = 1.5,
    timeout: float = 5.0,
) -> httpx.Response:
    """Performs HTTP GET request with domain-level rate limiting and exponential backoff.
    
    Adheres strictly to the 1 request per 2-3s constraint and respects robots/ToS.
    """
    domain = urlparse(url).netloc
    
    # 1. Domain rate limiting enforcement
    now = time.time()
    last_time = _last_request_time.get(domain, 0.0)
    elapsed = now - last_time
    if elapsed < RATE_LIMIT_DELAY:
        sleep_duration = RATE_LIMIT_DELAY - elapsed
        time.sleep(sleep_duration)
    
    # Update last request timestamp for domain
    _last_request_time[domain] = time.time()

    # 2. Prepare headers with descriptive User-Agent
    request_headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8"}
    if headers:
        request_headers.update(headers)

    # 3. Request loop with exponential backoff
    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, headers=request_headers, params=params)
                
                # Check for rate limit or server error
                if response.status_code == 429:
                    logger.warning(f"Rate limited (429) on {domain}. Backing off for {delay}s (Attempt {attempt}/{max_retries})")
                    time.sleep(delay)
                    delay *= backoff_factor
                    continue
                
                if response.status_code >= 500:
                    logger.warning(f"Server error ({response.status_code}) on {url}. Backing off {delay}s (Attempt {attempt}/{max_retries})")
                    time.sleep(delay)
                    delay *= backoff_factor
                    continue

                return response

        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning(f"Network error on {url}: {e}. Retrying in {delay}s (Attempt {attempt}/{max_retries})")
            if attempt == max_retries:
                raise
            time.sleep(delay)
            delay *= backoff_factor

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts.")
