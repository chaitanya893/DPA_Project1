import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def get_all_shopify_events():
    url = "https://investors.shopify.com/events"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-http2", "--no-sandbox"])
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            # Find and click any 'Past Events' buttons or load more
            buttons = await page.query_selector_all("button, a, .tab")
            for b in buttons:
                try:
                    txt = (await b.inner_text()).lower()
                    if "past" in txt or "archive" in txt or "previous" in txt or "load more" in txt:
                        print("Clicking tab/button:", txt)
                        await b.click()
                        await page.wait_for_timeout(2000)
                except Exception:
                    pass
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            for a in soup.find_all("a"):
                href = a.get("href", "")
                text = a.get_text(separator=" ", strip=True)
                if any(w in text.lower() or w in href.lower() for w in ["webcast", "quarter", "results", "financial", "earnings", "2025", "2024", "2023"]):
                    print(f"EVENT: {text} -> {href}")
        except Exception as e:
            print("Error:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_all_shopify_events())
