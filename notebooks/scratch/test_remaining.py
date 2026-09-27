import os, sys, time
import pandas as pd
from playwright.sync_api import sync_playwright

test_tickers = {
    'APT': ('https://alphaprotech.investorroom.com', 'ir_page_link'),
    'DMRC': ('https://edge.media-server.com/mmc/p/mmdzxsei/', 'press_release'),
    'RELL': ('https://rell.com/investor-relations', 'ir_page_link'),
    'PESI': ('https://www.webcaster5.com/Webcast/Page/2243/54338', 'press_release'),
    'RY': ('https://www.rbc.com/investorrelations/quarterly-financial-statements.html', 'press_release'),
    'ENB': ('https://events.q4inc.com/attendee/193728984', 'press_release'),
    'ABX': ('https://www.barrick.com/English/investors', 'ir_page_link'),
    'T': ('https://www.telus.com/en/about/investor-relations', 'ir_page_link'),
    'NTR': ('https://www.nutrien.com/investors', 'ir_page_link'),
    'MRU': ('https://corpo.metro.ca/en/investor-relations', 'ir_page_link'),
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-http2'])
    for ticker, (target_url, url_source) in test_tickers.items():
        print(f"\n--- Checking {ticker} ({target_url}) ---", flush=True)
        context = browser.new_context(
            user_agent="EarningsCallCaptureBot/1.0 (Contact: research_intern@domain.com)",
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True
        )
        page = context.new_page()
        http_status = 200
        try:
            resp = page.goto(target_url, wait_until='domcontentloaded', timeout=15000)
            if resp:
                http_status = resp.status
        except Exception as e:
            print(f"[{ticker}] Goto note: {e}", flush=True)
            http_status = 403
            
        # If ir_page_link, find specific links
        if url_source == 'ir_page_link' and http_status == 200:
            try:
                page.wait_for_timeout(2000)
                links = page.evaluate("""() => {
                    const res = [];
                    for (const a of document.querySelectorAll('a')) {
                        const text = (a.innerText || '').trim();
                        const href = a.href;
                        if (href && !href.startsWith('javascript') && !href.endsWith('#')) {
                            res.push({text, href});
                        }
                    }
                    return res;
                }""")
                for item in links:
                    t = item['text'].lower()
                    h = item['href'].lower()
                    if any(w in t for w in ['webcast', 'conference call', 'events & presentations', 'events and presentations', 'events', 'quarterly results', 'investor presentation']):
                        if item['href'] != target_url:
                            print(f"[{ticker}] Navigating to: {item['text']} -> {item['href']}", flush=True)
                            target_url = item['href']
                            try:
                                resp2 = page.goto(target_url, wait_until='domcontentloaded', timeout=15000)
                                if resp2:
                                    http_status = resp2.status
                            except Exception as e:
                                print(f"[{ticker}] Follow link note: {e}", flush=True)
                            break
            except:
                pass
                
        # Wait until no Loading text (max 20s)
        start_wait = time.time()
        while time.time() - start_wait < 15:
            try:
                body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
                if "loading..." not in body_text.lower() and len(body_text.strip()) > 30:
                    break
            except:
                break
            time.sleep(1)
            
        # Count form inputs
        form_inputs_count = 0
        body_text = ""
        try:
            form_inputs_count = page.evaluate("""() => {
                let count = 0;
                const inputs = document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select');
                for (const inp of inputs) {
                    const rect = inp.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        count++;
                    }
                }
                return count;
            }""")
            body_text = page.evaluate("() => document.body ? document.body.innerText : ''").lower()
        except:
            pass
            
        print(f"[{ticker}] Final URL: {target_url} | HTTP: {http_status} | Inputs: {form_inputs_count} | Body sample: {body_text[:120]}...", flush=True)
        context.close()
        
    browser.close()
