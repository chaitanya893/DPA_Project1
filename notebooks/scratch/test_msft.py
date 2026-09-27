import asyncio
from playwright.async_api import async_playwright

async def test_msft_medius():
    url = "https://medius.microsoft.com/Embed/video-nc/55b7ccb2-44c5-4ddd-8c69-696af249231f"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-http2", "--no-sandbox"])
        page = await browser.new_page()
        m3u8_links = []
        page.on("response", lambda r: m3u8_links.append(r.url) if (".m3u8" in r.url.lower() or "stream.event.microsoft.com" in r.url.lower() or "mp4" in r.url.lower()) else None)
        try:
            print("Navigating to medius iframe...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            btns = await page.query_selector_all("button, .vjs-big-play-button, .play-button, .vjs-play-control")
            print("Found buttons:", len(btns))
            for b in btns:
                try:
                    if await b.is_visible():
                        print("Clicking button...")
                        await b.click()
                        await page.wait_for_timeout(3000)
                except Exception as e:
                    print("Button click error:", e)
            await page.wait_for_timeout(5000)
            print("Captured Media URLs:")
            for m in m3u8_links:
                print("  ->", m)
        except Exception as e:
            print("Error:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_msft_medius())
