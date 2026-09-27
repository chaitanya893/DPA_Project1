import asyncio
from playwright.async_api import async_playwright

async def test_urls():
    urls = [
        ('LMB', 'https://event.choruscall.com/mediaframe/webcast.html?webcastid=LYkmLAUY'),
        ('ENB', 'https://events.q4inc.com/attendee/193728984'),
        ('CNR', 'https://event.webcasts.com/starthere.jsp?ei=1774946&tp_key=06654de884&tp_special=8'),
        ('SAP', 'https://www.gowebcasting.com/13127'),
    ]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--disable-http2', '--no-sandbox'])
        for ticker, url in urls:
            print(f"=== Testing {ticker} ({url}) ===")
            page = await browser.new_page()
            media = []
            page.on('response', lambda r: media.append(r.url) if any(ext in r.url.lower() for ext in ['.m3u8', '.mp3', '.mp4', '.m4a']) else None)
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(5000)
                btns = await page.query_selector_all('button, .play, .vjs-big-play-button')
                for b in btns[:3]:
                    try:
                        await b.click(timeout=1000)
                    except Exception:
                        pass
                await page.wait_for_timeout(5000)
                print(f"{ticker} media captured: {media}")
            except Exception as e:
                print(f"{ticker} error: {e}")
            finally:
                await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_urls())
