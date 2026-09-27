import asyncio
import json
import re
import urllib.parse
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import requests

from src.utils.logger import setup_logger
from src.capture.stream_downloader import _enforce_rate_limit, USER_AGENT

logger = setup_logger("msft_parser")


def parse_msft_event_page_static(event_page_url: str) -> Dict[str, Any]:
    """Inspects Microsoft investor event page for iframe embed URL and company-published transcript link."""
    _enforce_rate_limit(event_page_url)
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ({USER_AGENT})"}
    res = requests.get(event_page_url, headers=headers, timeout=15)
    if res.status_code != 200:
        return {"error": f"HTTP {res.status_code} at {event_page_url}"}

    soup = BeautifulSoup(res.text, "html.parser")
    
    iframe_src: Optional[str] = None
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "").strip()
        if "medius.microsoft.com" in src or "mediastream.microsoft.com" in src:
            iframe_src = src
            break

    transcript_url: Optional[str] = None
    for a in soup.find_all("a"):
        h = a.get("href", "").strip()
        t = a.get_text(separator=" ", strip=True).lower()
        if "transcript" in h.lower() or "transcript" in t:
            if h.startswith("http"):
                transcript_url = h
            elif h.startswith("/"):
                transcript_url = urllib.parse.urljoin("https://www.microsoft.com", h)
            break

    return {
        "iframe_src": iframe_src,
        "transcript_url": transcript_url,
        "raw_html": res.text,
    }


async def sniff_medius_m3u8(iframe_url: str, timeout_sec: int = 35) -> Optional[str]:
    """
    Variant A: Opens Medius player iframe in Playwright.
    Clicks the center of video area / big play overlay (fallback: muted video.play()).
    Waits 6-8s, reads stream URL via performance entries and network response interception.
    Uses master.m3u8 on stream.event.microsoft.com.
    """
    _enforce_rate_limit(iframe_url)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-http2", "--no-sandbox", "--disable-setuid-sandbox", "--autoplay-policy=no-user-gesture-required"]
        )
        page = await browser.new_page()
        m3u8_links = []

        def on_resp(r):
            u = r.url
            if ".m3u8" in u.lower() and "stream.event.microsoft.com" in u.lower():
                m3u8_links.append(u)
            elif ".m3u8" in u.lower() and ("mseventstream" in u.lower() or "azureedge" in u.lower() or "medius" in u.lower()):
                m3u8_links.append(u)

        page.on("response", on_resp)
        try:
            await page.goto(iframe_url, wait_until="domcontentloaded", timeout=timeout_sec * 1000)
            await page.wait_for_timeout(3000)

            # 1. Click center of viewport / video area
            vp = page.viewport_size or {"width": 1280, "height": 720}
            try:
                await page.mouse.click(vp["width"] / 2, vp["height"] / 2)
            except Exception:
                pass

            # 2. Fallback: JavaScript play trigger with muted video
            try:
                await page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) {
                        v.muted = true;
                        v.play().catch(() => {});
                    }
                }""")
            except Exception:
                pass

            # 3. Wait 6-8 s
            await page.wait_for_timeout(7000)

            # 4. Read performance resource entries
            try:
                perf_entries = await page.evaluate("""() => {
                    return performance.getEntriesByType('resource')
                        .map(r => r.name)
                        .filter(n => n.includes('.m3u8'));
                }""")
                for pe in perf_entries:
                    if pe not in m3u8_links:
                        m3u8_links.append(pe)
            except Exception:
                pass

            # Filter for master.m3u8 on stream.event.microsoft.com
            master_links = [u for u in m3u8_links if "master.m3u8" in u.lower() and "stream.event.microsoft.com" in u.lower()]
            if master_links:
                return master_links[0]
            
            event_links = [u for u in m3u8_links if "stream.event.microsoft.com" in u.lower()]
            if event_links:
                return event_links[0]

            return m3u8_links[0] if m3u8_links else None

        except Exception as e:
            logger.warning(f"Error sniffing Medius stream at {iframe_url}: {e}")
            return None
        finally:
            await browser.close()


def sniff_mediastream_json(iframe_url: str) -> Optional[str]:
    """Variant B: Parses player.html?path=... config JSON and constructs master.m3u8 stream endpoint."""
    parsed = urllib.parse.urlparse(iframe_url)
    qs = urllib.parse.parse_qs(parsed.query)
    json_path = qs.get("path", [""])[0]
    if not json_path:
        return None

    full_json_url = f"https://mediastream.microsoft.com{json_path}" if json_path.startswith("/") else f"https://mediastream.microsoft.com/{json_path}"
    _enforce_rate_limit(full_json_url)
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ({USER_AGENT})"}
    res = requests.get(full_json_url, headers=headers, timeout=15)
    if res.status_code != 200:
        return None

    data = res.json()
    
    # Extract hostName and manifest path
    host_name = "https://stream.event.microsoft.com/prodwe"
    manifest_path = None

    def search_manifest(obj):
        nonlocal host_name, manifest_path
        if isinstance(obj, dict):
            if "hostName" in obj and "stream.event.microsoft.com" in str(obj["hostName"]):
                host_name = obj["hostName"].rstrip("/")
            if "manifest" in obj and "master.m3u8" in str(obj["manifest"]):
                manifest_path = obj["manifest"]
            for v in obj.values():
                search_manifest(v)
        elif isinstance(obj, list):
            for x in obj:
                search_manifest(x)

    search_manifest(data)
    if manifest_path:
        m_clean = "/" + manifest_path.lstrip("/")
        return f"{host_name}{m_clean}"
    return None


async def parse_msft_call(event_page_url: str, fiscal_period: str) -> Dict[str, Any]:
    """Full parser for Microsoft investor event page."""
    static_data = parse_msft_event_page_static(event_page_url)
    if "error" in static_data:
        return {"error": static_data["error"]}

    iframe_src = static_data.get("iframe_src")
    transcript_url = static_data.get("transcript_url")

    if not iframe_src:
        return {"error": f"No video iframe found on {event_page_url}"}

    m3u8_url: Optional[str] = None
    if "medius.microsoft.com" in iframe_src:
        m3u8_url = await sniff_medius_m3u8(iframe_src)
    elif "mediastream.microsoft.com" in iframe_src:
        m3u8_url = sniff_mediastream_json(iframe_src)
        if not m3u8_url:
            m3u8_url = await sniff_medius_m3u8(iframe_src)

    if not m3u8_url:
        return {"error": f"No media stream URL captured from {iframe_src}"}

    return {
        "ticker": "MSFT",
        "fiscal_period": fiscal_period,
        "event_page_url": event_page_url,
        "media_url": m3u8_url,
        "transcript_url": transcript_url,
        "publisher": "Microsoft IR",
    }
