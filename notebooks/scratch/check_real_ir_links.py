import os, sys, time
from playwright.sync_api import sync_playwright

sites = {
    'MRU': 'https://corpo.metro.ca/en/investor-relations.html',
    'ABX': 'https://www.barrick.com/English/investors/default.aspx',
    'JNJ': 'https://investor.jnj.com',
    'XOM': 'https://investor.exxonmobil.com',
    'WMT': 'https://stock.walmart.com',
    'APT': 'https://alphaprotech.com',
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-http2'])
    for ticker, url in sites.items():
        print(f"\n=================== {ticker} ({url}) ===================")
        page = browser.new_page()
        try:
            resp = page.goto(url, timeout=15000)
            print(f"Status: {resp.status if resp else 'None'}")
            # get links
            page.wait_for_timeout(2000)
            links = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => ({text: (a.innerText||'').trim(), href: a.href}))""")
            for l in links:
                t = l['text'].lower()
                h = l['href'].lower()
                if any(w in t or w in h for w in ['webcast', 'conference', 'presentation', 'events', 'quarter', 'results', 'earnings', 'investor']):
                    if l['href'] != url and not l['href'].endswith('#'):
                        print(f"  Link: {l['text']} -> {l['href']}")
        except Exception as e:
            print(f"Error: {e}")
        page.close()
    browser.close()
