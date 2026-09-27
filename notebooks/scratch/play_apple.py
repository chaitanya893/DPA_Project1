import asyncio
from playwright.async_api import async_playwright

async def play_and_capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        captured_media = []
        def on_response(response):
            u = response.url
            if any(ext in u.lower() for ext in [".m3u8", ".mp4", ".m4a", ".mp3", ".aac", "vod", "hls", "audio"]):
                if not any(x in u.lower() for x in [".js", ".css", ".png", ".jpg", ".svg", "beacon", "analytics"]):
                    captured_media.append((response.status, u))
                    print(f"Captured Media Response: {response.status} {u}")
                    
        page.on("response", on_response)
        
        print("Navigating to Apple earnings call page...")
        await page.goto("https://www.apple.com/investor/earnings-call/", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Click play button or video player
        buttons = await page.query_selector_all("button, .play-button, [aria-label*='Play'], [aria-label*='listen'], .icon-play")
        print(f"Found {len(buttons)} play buttons")
        for b in buttons:
            try:
                print("Clicking play button...")
                await b.click()
                await page.wait_for_timeout(4000)
            except Exception as e:
                print("Click error:", e)
                
        print(f"Total media captured: {len(captured_media)}")
        for status, u in captured_media:
            print(f"  {status} -> {u}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(play_and_capture())
