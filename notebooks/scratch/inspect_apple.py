import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

async def inspect_apple():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        media_reqs = []
        page.on("request", lambda r: media_reqs.append(r.url) if any(x in r.url.lower() for x in [".m3u8", ".mp3", ".mp4", ".m4a", ".aac", "audio", "stream", "hls", "apple.com"]) and not any(y in r.url.lower() for y in [".js", ".css", ".png", ".jpg", ".svg", "analytics"]) else None)
        
        await page.goto("https://www.apple.com/investor/earnings-call/", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        print("Page title:", soup.title.string if soup.title else "No title")
        for a in soup.find_all(["a", "button", "audio", "video", "source"]):
            h = a.get("href") or a.get("src") or ""
            text = a.get_text(strip=True)
            if any(k in h.lower() or k in text.lower() for k in ["listen", "webcast", "audio", "replay", "q3", "q4", "q2", "q1", "download"]):
                print(f"  Element: [{text}] -> {h}")
                
        print("Media requests triggered:")
        for r in media_reqs[:10]:
            print(f"  Req: {r}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_apple())
