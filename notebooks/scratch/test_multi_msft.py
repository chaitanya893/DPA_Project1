import asyncio
from playwright.async_api import async_playwright

async def sniff_msft_stream(iframe_url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-http2", "--no-sandbox"])
        page = await browser.new_page()
        m3u8_links = []
        page.on("response", lambda r: m3u8_links.append(r.url) if (".m3u8" in r.url.lower() and "master" in r.url.lower()) else None)
        try:
            await page.goto(iframe_url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(3000)
            btns = await page.query_selector_all("button, .vjs-big-play-button, .play-button, .vjs-play-control")
            for b in btns[:3]:
                try:
                    if await b.is_visible():
                        await b.click()
                        await page.wait_for_timeout(2000)
                except Exception:
                    pass
            await page.wait_for_timeout(4000)
            return m3u8_links[0] if m3u8_links else None
        finally:
            await browser.close()

async def main():
    iframes = [
        ("MSFT_FY26_Q4", "https://medius.microsoft.com/Embed/video-nc/55b7ccb2-44c5-4ddd-8c69-696af249231f"),
        ("MSFT_FY26_Q3", "https://medius.microsoft.com/Embed/video-nc/547ca906-a8b4-4f7a-bd53-844a9032fb54"),
        ("MSFT_FY26_Q2", "https://medius.microsoft.com/Embed/video-nc/61d9a257-6b57-4953-98f0-7c49ed2dce32?r=64992262542"),
        ("MSFT_FY26_Q1", "https://medius.microsoft.com/Embed/video-nc/3877d0ae-114a-4e2e-9a17-85f3b7a81502"),
        ("MSFT_FY25_Q4", "https://medius.microsoft.com/Embed/video-nc/15ea4a91-4aea-4da4-b94b-77b4613af6f5?r=681481682673"),
        ("MSFT_FY25_Q1", "https://medius.microsoft.com/Embed/video-nc/2a2c015a-7c18-4a83-8dcc-597937e3b789"),
    ]
    for label, u in iframes:
        stream = await sniff_msft_stream(u)
        print(f"{label} -> {stream}")

if __name__ == "__main__":
    asyncio.run(main())
