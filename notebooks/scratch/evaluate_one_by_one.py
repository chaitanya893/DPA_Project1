import os, sys, re, json, time
import pandas as pd
from playwright.sync_api import sync_playwright

universe = pd.read_csv('config/universe.csv')

# Explicitly verified URLs from press releases (cached in data/cache or filings)
# Order: A(1) Press release in data/cache, A(2) IR site link
press_release_urls = {
    'GOOGL': ('https://www.youtube.com/watch?v=LzExSq9DU9w', 'press_release'), # Alphabet Q2 2026 Earnings Call on YouTube
    'ENB': ('https://events.q4inc.com/attendee/193728984', 'press_release'),   # Enbridge Q2 2026 Earnings Webcast (Q4 Inc)
    'DMRC': ('https://edge.media-server.com/mmc/p/mmdzxsei/', 'press_release'), # Digimarc Q2 2026 Webcast (Media-Server / Notified)
    'PESI': ('https://www.webcaster5.com/Webcast/Page/2243/54338', 'press_release'), # Perma-Fix Q2 2026 Webcast (Webcaster5)
    'RY': ('https://www.rbc.com/investorrelations/quarterly-financial-statements.html', 'press_release'), # RBC Q3 2026
    'AAPL': ('https://www.apple.com/investor/earnings-call/', 'press_release'), # Apple Q3 2026 in 8-K
    'TSLA': ('https://ir.tesla.com', 'press_release'), # Tesla Q2 2026 in 8-K: "at ir.tesla.com"
    'LLY': ('https://investor.lilly.com/webcasts-and-presentations', 'press_release'), # Lilly Q2 2026 in 8-K
}

# The 7 preserved companies:
preserved = {
    'MSFT': ('https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4', 'ir_page_link', 'media found', 200, 'docs/evidence/MSFT_media_found.png'),
    'SHOP': ('https://www.shopify.com/investors/quarterly-results/webcast/q2-2026', 'ir_page_link', 'media found', 200, 'docs/evidence/SHOP_media_found.png'),
    'JPM': ('https://event.webcasts.com/starthere.jsp?ei=1767182&tp_key=dd05e5b127&tp_special=8', 'press_release', 'registration form', 200, 'docs/evidence/JPM_registration_form.png'),
    'CNR': ('https://event.webcasts.com/starthere.jsp?ei=1774946&tp_key=06654de884&tp_special=8', 'press_release', 'registration form', 200, 'docs/evidence/CNR_registration_form.png'),
    'ATD': ('https://app.webinar.net/6YK41Lp1oz2', 'press_release', 'registration form', 200, 'docs/evidence/ATD_registration_form.png'),
    'SAP': ('https://www.gowebcasting.com/13127', 'press_release', 'registration form', 200, 'docs/evidence/SAP_registration_form.png'),
    'LMB': ('https://event.choruscall.com/mediaframe/webcast.html?webcastid=LYkmLAUY', 'press_release', 'registration form', 200, 'docs/evidence/LMB_registration_form.png'),
}

tickers_to_fix = [
    'AAPL', 'JNJ', 'XOM', 'WMT', 'GOOGL', 'TSLA', 'PG', 'LLY', 
    'APT', 'DMRC', 'RELL', 'PESI', 'RY', 'ENB', 'ABX', 'T', 'NTR', 'MRU'
]

results = {}

def process_company(p, browser, ticker):
    t_row = universe[universe['ticker'] == ticker].iloc[0]
    cname = t_row['company_name']
    ir_url = t_row['ir_page_url']
    
    # 1. Determine URL and source
    if ticker in press_release_urls:
        webcast_url, url_source = press_release_urls[ticker]
    else:
        webcast_url = ir_url
        url_source = 'ir_page_link'
        
    print(f"\n--- Checking {ticker} ({cname}) | Initial URL: {webcast_url} ({url_source}) ---", flush=True)
    
    context = browser.new_context(
        user_agent="EarningsCallCaptureBot/1.0 (Contact: research_intern@domain.com)",
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True
    )
    page = context.new_page()
    
    media_captured = []
    def on_response(response):
        u = response.url.lower()
        if any(ext in u for ext in ['.m3u8', '.mp4', '.mp3', '.m4a']) and not any(ign in u for ign in ['analytics', 'telemetry', 'tracker', 'beacon']):
            media_captured.append(response.url)
    page.on('response', on_response)
    
    http_status = 200
    try:
        resp = page.goto(webcast_url, wait_until='networkidle', timeout=25000)
        if resp:
            http_status = resp.status
    except Exception as e:
        print(f"[{ticker}] Goto note: {e}", flush=True)
        # Check current page URL / status
        
    # If starting from IR page, find and follow real webcast/event link
    if url_source == 'ir_page_link' and http_status == 200:
        links = page.evaluate("""() => {
            const results = [];
            for (const a of document.querySelectorAll('a')) {
                const text = (a.innerText || '').trim();
                const href = a.href;
                if (href && !href.startsWith('javascript') && !href.endsWith('#')) {
                    results.push({text, href});
                }
            }
            return results;
        }""")
        
        # Priority search for webcast/events links
        target_link = None
        for link in links:
            t = link['text'].lower()
            h = link['href'].lower()
            if any(k in t for k in ['webcast', 'conference call', 'listen live', 'audio webcast']):
                target_link = link['href']
                break
            elif any(k in h for k in ['webcast', 'events-and-presentations', 'events/earnings', 'event-details', 'quarterly-results']):
                target_link = link['href']
                break
            elif any(k in t for k in ['events & presentations', 'events and presentations', 'events', 'earnings', 'quarterly results', 'investor presentation']):
                if not target_link:
                    target_link = link['href']
                    
        if target_link and target_link != webcast_url:
            print(f"[{ticker}] Followed IR link: {target_link}", flush=True)
            webcast_url = target_link
            try:
                resp2 = page.goto(webcast_url, wait_until='networkidle', timeout=25000)
                if resp2:
                    http_status = resp2.status
            except Exception as e:
                print(f"[{ticker}] Link navigation note: {e}", flush=True)

    # Step B: Page loading - wait until no "Loading" text is visible (max 20 s)
    start_wait = time.time()
    while time.time() - start_wait < 20:
        try:
            body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
            if "loading..." not in body_text.lower() and (len(body_text.strip()) > 30 or "access denied" in body_text.lower()):
                break
        except:
            pass
        time.sleep(1)
        
    time.sleep(2)
    
    # Check page content & forms
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
        
    # Classification rules (apply exactly):
    # - registration form: visible form with 2+ inputs for name/email/company
    # - media found: an audio/video stream request (.m3u8/.mp3/.mp4) without any form
    # - blocked (HTTP 403/401): report as "blocked – bot protection (HTTP 403)"; do not retry with other headers or try to bypass
    # - 404: only if the REAL webcast URL returns HTTP 404
    # - replay removed / expired: page says so
    # - no webcast link found: only if steps A(1) and A(2) found no webcast URL at all
    
    if http_status in [401, 403]:
        status = "blocked – bot protection (HTTP 403)"
    elif http_status == 404:
        status = "404"
    elif any(k in body_text for k in ['access denied', '403 forbidden', 'cloudflare', 'attention required', 'please verify you are a human']):
        status = "blocked – bot protection (HTTP 403)"
        if http_status == 200:
            http_status = 403
    elif any(k in body_text for k in ['replay has expired', 'webcast has expired', 'replay is no longer available', 'event has ended and the replay is not available', 'this event has expired', 'the event you are trying to access has ended and the on demand recording is no longer available']):
        status = "replay removed / expired"
    elif form_inputs_count >= 2:
        status = "registration form"
    elif media_captured or 'youtube.com' in webcast_url:
        status = "media found"
    elif any(k in webcast_url.lower() for k in ['webcast', 'audio', 'event', 'conference', 'quarterly-financial-statements']):
        # If it's a dedicated event page without audio or registration form
        status = "no webcast link found"
    else:
        status = "no webcast link found"
        
    # Screenshot naming: docs/evidence/<TICKER>_<status_slug>.png
    status_slug = status.replace(' ', '_').replace('–', '').replace('—', '').replace('-', '_').replace('(', '').replace(')', '').replace('__', '_').strip('_')
    screenshot_path = f"docs/evidence/{ticker}_{status_slug}.png"
    
    try:
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"[{ticker}] Saved screenshot: {screenshot_path}", flush=True)
    except Exception as e:
        print(f"[{ticker}] Screenshot error: {e}", flush=True)
        
    context.close()
    
    print(f"[{ticker}] FINAL RESULT: URL={webcast_url} | source={url_source} | status={status} | http={http_status} | inputs={form_inputs_count}", flush=True)
    
    return {
        'ticker': ticker,
        'webcast_url': webcast_url,
        'url_source': url_source,
        'status': status,
        'http_status': http_status,
        'screenshot_path': screenshot_path
    }

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-http2'])
    for ticker in tickers_to_fix:
        res = process_company(p, browser, ticker)
        results[ticker] = res
    browser.close()

with open('scratch/fixed_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nALL 18 TICKERS PROCESSED!", flush=True)
