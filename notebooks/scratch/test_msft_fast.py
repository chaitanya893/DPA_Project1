import asyncio
from playwright.async_api import async_playwright

async def test_sniff_msft_fast():
    urls = [
        ("MSFT_FY26_Q4", "https://medius.microsoft.com/Embed/video-nc/55b7ccb2-44c5-4ddd-8c69-696af249231f"),
        ("MSFT_FY26_Q3", "https://medius.microsoft.com/Embed/video-nc/547ca906-a8b4-4f7a-bd53-844a9032fb54"),
        ("MSFT_FY26_Q2", "https://medius.microsoft.com/Embed/video-nc/61d9a257-6b57-4953-98f0-7c49ed2dce32?r=64992262542"),
    ]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-http2", "--no-sandbox"])
        context = await browser.new_context()
        for label, u in urls:
            page = await context.new_page()
            streams = []
            page.on("response", lambda r: streams.append(r.url) if (".m3u8" in r.url.lower() and "master" in r.url.lower()) else None)
            try:
                await page.goto(u, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)
                btns = await page.query_selector_all("button, .vjs-big-play-button, .play-button")
                for b in btns[:2]:
                    try:
                        await b.click()
                    except Exception:
                        pass
                await page.wait_for_timeout(3000)
                print(f"{label} -> {streams[0] if streams else 'None'}")
            finally:
                await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_sniff_msft_fast())
