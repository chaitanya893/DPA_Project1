import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def get_shopify_events():
    url = "https://investors.shopify.com/events"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-http2", "--no-sandbox"])
        page = await browser.new_page()
        try:
            print("Opening Shopify events page...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            print("--- Found Links ---")
            for a in soup.find_all("a"):
                t = a.get_text(separator=" ", strip=True)
                h = a.get("href", "")
                if any(w in t.lower() or w in h.lower() for w in ["quarter", "earnings", "q1", "q2", "q3", "q4", "2025", "2026", "2024", "financial-results"]):
                    print(f"Text: {t[:60]} | Href: {h}")
        except Exception as e:
            print("Error:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(get_shopify_events())
