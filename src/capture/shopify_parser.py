import asyncio
import urllib.parse
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import requests

from src.utils.logger import setup_logger
from src.capture.stream_downloader import _enforce_rate_limit, USER_AGENT

logger = setup_logger("shopify_parser")


def parse_shopify_event_page_static(event_page_url: str) -> Dict[str, Any]:
    """Inspects Shopify webcast page for transcripts and confirms availability."""
    _enforce_rate_limit(event_page_url)
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ({USER_AGENT})"}
    res = requests.get(event_page_url, headers=headers, timeout=15)
    if res.status_code == 404:
        return {"error": f"404 at {event_page_url}"}
    if res.status_code != 200:
        return {"error": f"HTTP {res.status_code} at {event_page_url}"}

    soup = BeautifulSoup(res.text, "html.parser")
    transcript_url: Optional[str] = None
    for a in soup.find_all("a"):
        h = a.get("href", "").strip()
        t = a.get_text(separator=" ", strip=True).lower()
        if "transcript" in h.lower() or "transcript" in t:
            if h.startswith("http"):
                transcript_url = h
            elif h.startswith("/"):
                transcript_url = urllib.parse.urljoin("https://investors.shopify.com", h)
            break

    return {
        "transcript_url": transcript_url,
        "raw_html": res.text,
    }


async def sniff_shopify_m3u8(event_page_url: str, timeout_sec: int = 30) -> Optional[str]:
    """Opens Shopify event page in Playwright, clicks play, intercepts stream.mux.com .m3u8."""
    _enforce_rate_limit(event_page_url)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-http2", "--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        m3u8_links = []

        def on_resp(r):
            u = r.url
            if "stream.mux.com" in u.lower() and ".m3u8" in u.lower():
                m3u8_links.append(u)

        page.on("response", on_resp)
        try:
            await page.goto(event_page_url, wait_until="domcontentloaded", timeout=timeout_sec * 1000)
            await page.wait_for_timeout(3000)
            btns = await page.query_selector_all("button, .play-button, .vjs-big-play-button")
            for b in btns[:2]:
                try:
                    if await b.is_visible():
                        await b.click(timeout=1500)
                        await page.wait_for_timeout(2000)
                except Exception:
                    pass
            await page.wait_for_timeout(4000)
            return m3u8_links[0] if m3u8_links else None
        except Exception as e:
            logger.warning(f"Error sniffing Shopify stream at {event_page_url}: {e}")
            return None
        finally:
            await browser.close()


async def parse_shopify_call(event_page_url: str, fiscal_period: str) -> Dict[str, Any]:
    """Full parser for Shopify webcast page."""
    static_data = parse_shopify_event_page_static(event_page_url)
    if "error" in static_data:
        return {"error": static_data["error"]}

    transcript_url = static_data.get("transcript_url")
    m3u8_url = await sniff_shopify_m3u8(event_page_url)

    if not m3u8_url:
        return {"error": f"no media stream found at {event_page_url}"}

    return {
        "ticker": "SHOP",
        "fiscal_period": fiscal_period,
        "event_page_url": event_page_url,
        "media_url": m3u8_url,
        "transcript_url": transcript_url,
        "publisher": "Shopify IR",
    }
