import asyncio
import os
import urllib.parse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from src.db.session import SessionLocal
from src.db.models import EventRegistry, CompanyUniverse

async def discover_media_for_company(ticker, url, ir_page_url):
    print(f"\n=== Testing {ticker} === (webcast: {url}, IR: {ir_page_url})")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (FinancialResearch/1.0; contact@academic-research.org)")
        page = await context.new_page()
        
        media_urls = []
        def req_handler(req):
            u = req.url
            if any(ext in u.lower() for ext in [".m3u8", ".mp3", ".mp4", ".m4a", ".aac", "audio", "stream", "token", "vod"]):
                if not any(x in u.lower() for x in [".js", ".css", ".svg", ".png", ".jpg", "font", "analytics", "telemetry"]):
                    media_urls.append(u)
        
        page.on("request", req_handler)
        
        target_url = url if url and url.startswith("http") else ir_page_url
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            content = await page.content()
            
            has_reg = False
            if any(term in content.lower() for term in ["please register", "registration required", "first name", "last name", "email address", "enter your email", "register for webcast"]):
                inputs = await page.query_selector_all("input")
                if len(inputs) >= 2:
                    has_reg = True
                    print(f"{ticker}: Registration form detected ({len(inputs)} fields)")
            
            soup = BeautifulSoup(content, "html.parser")
            for a in soup.find_all(["a", "audio", "video", "source"]):
                href = a.get("href") or a.get("src")
                if href:
                    h_full = urllib.parse.urljoin(target_url, href)
                    if any(ext in h_full.lower() for ext in [".mp3", ".m4a", ".mp4", ".m3u8", ".wav"]):
                        media_urls.append(h_full)
                        
            print(f"{ticker}: Result -> media_urls={len(media_urls)}, has_reg={has_reg}")
            for m in media_urls[:5]:
                print(f"  -> {m[:120]}")
        except Exception as e:
            print(f"{ticker}: Exception -> {e}")
        finally:
            await browser.close()

async def main():
    db = SessionLocal()
    events = db.query(EventRegistry).join(CompanyUniverse).all()
    priority = ["AAPL", "MSFT", "JPM", "JNJ", "GOOGL", "TSLA", "LLY", "LMB", "RELL", "RY", "ENB", "CNR", "SHOP", "ATD", "MRU", "SAP"]
    ev_map = {e.ticker: e for e in events}
    for t in priority:
        if t in ev_map:
            ev = ev_map[t]
            await discover_media_for_company(t, ev.webcast_url, ev.company.ir_page_url)

if __name__ == "__main__":
    asyncio.run(main())
