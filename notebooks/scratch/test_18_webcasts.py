import os, sys, re, json, time
import pandas as pd
from playwright.sync_api import sync_playwright

universe = pd.read_csv('config/universe.csv')

# Let's inspect the cached filings for any explicit webcast URLs for all 18 tickers
cache_dir = 'data/cache'
cached_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.json')]
docs = []
for f in cached_files:
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            data = json.load(fp)
            docs.append((f, data.get('url', ''), data.get('content', '') or data.get('text', '') or data.get('html', '') or ''))
    except:
        pass

def get_url_from_cache(ticker, cname, cik):
    for fpath, url, content in docs:
        is_match = False
        if cik and cik != 'NONE' and cik != 'nan' and (f"/{cik}/" in url or f"data/{cik}" in url):
            is_match = True
        elif ticker.lower() in url.lower():
            is_match = True
        elif cname.lower() in content[:1000].lower():
            is_match = True
            
        if is_match:
            # Look for webcast section
            paras = re.split(r'\n{2,}|\.\s+', content)
            for p in paras:
                if any(w in p.lower() for w in ['webcast', 'conference call', 'listen live', 'audio webcast']):
                    # Look for URLs
                    # Remove trailing punctuation
                    urls = re.findall(r'https?://[^\s<>"\'\)]+', p)
                    for u in urls:
                        u_clean = u.rstrip('.,;:')
                        if any(k in u_clean.lower() for k in ['youtube.com', 'webcast', 'webcaster', 'choruscall', 'webinar', 'q4inc', 'gowebcasting', 'on24.com', 'event', 'investor', 'financial-statements']):
                            return u_clean, 'press_release'
    return None, None

def inspect_ticker(p, browser, ticker):
    t_row = universe[universe['ticker'] == ticker].iloc[0]
    cname = t_row['company_name']
    cik = str(t_row.get('sec_cik', ''))
    ir_url = t_row['ir_page_url']
    
    # 1. Try cache press release
    webcast_url, url_source = get_url_from_cache(ticker, cname, cik)
    if webcast_url:
        print(f"[{ticker}] Found in cache press release: {webcast_url}")
    else:
        # 2. Try IR page navigation
        print(f"[{ticker}] Checking IR page: {ir_url}")
        webcast_url = ir_url
        url_source = 'ir_page_link'
        
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
        resp = page.goto(webcast_url, wait_until='networkidle', timeout=30000)
        if resp:
            http_status = resp.status
    except Exception as e:
        print(f"[{ticker}] Goto error: {e}")
        http_status = 500
        
    # If this was the IR page and we want to find a link whose text contains 'webcast', 'conference call', 'listen' or fiscal period
    if url_source == 'ir_page_link' and http_status == 200:
        links = page.evaluate("""() => {
            const results = [];
            for (const a of document.querySelectorAll('a')) {
                const text = (a.innerText || '').trim();
                const href = a.href;
                if (href && (text.toLowerCase().includes('webcast') || text.toLowerCase().includes('conference call') || text.toLowerCase().includes('listen') || text.toLowerCase().includes('q2 2026') || text.toLowerCase().includes('q3 2026') || text.toLowerCase().includes('q4 2025') || text.toLowerCase().includes('q1 2026') || text.toLowerCase().includes('events & presentations') || text.toLowerCase().includes('events and presentations') || text.toLowerCase().includes('events') || text.toLowerCase().includes('earnings'))) {
                    results.push({text, href});
                }
            }
            return results;
        }""")
        print(f"[{ticker}] Discovered IR links: {links[:5]}")
        # If there's a specific webcast link, follow it
        for link in links:
            if any(k in link['text'].lower() for k in ['webcast', 'conference call', 'listen', 'q2 2026', 'q3 2026', 'q1 2026']) or any(k in link['href'].lower() for k in ['webcast', 'event', 'audio', 'q4inc', 'webcasts.com', 'choruscall', 'webinar.net', 'gowebcasting']):
                if link['href'] != webcast_url and not link['href'].endswith('#'):
                    print(f"[{ticker}] Navigating to link: {link['text']} -> {link['href']}")
                    webcast_url = link['href']
                    try:
                        resp2 = page.goto(webcast_url, wait_until='networkidle', timeout=30000)
                        if resp2:
                            http_status = resp2.status
                    except Exception as e:
                        print(f"[{ticker}] Error navigating to link: {e}")
                    break

    # Wait until no "Loading" text is visible (max 20s)
    start_wait = time.time()
    while time.time() - start_wait < 20:
        body_text = page.evaluate("() => document.body ? document.body.innerText : ''")
        if "loading" not in body_text.lower() or "loading..." not in body_text.lower():
            # If body has substantial text and loading is not the main thing
            if len(body_text.strip()) > 50 and "loading..." not in body_text.lower():
                break
        time.sleep(1)
        
    time.sleep(3)
    
    # Classify page
    # Check for visible forms
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
    
    status = "unclassified"
    if http_status in [401, 403]:
        status = "blocked – bot protection (HTTP 403)"
    elif http_status == 404:
        status = "404"
    elif any(k in body_text for k in ['replay has expired', 'webcast has expired', 'replay is no longer available', 'event has ended and the replay is not available', 'this event has expired']):
        status = "replay removed / expired"
    elif form_inputs_count >= 2:
        status = "registration form"
    elif media_captured:
        status = "media found"
    elif any(k in body_text for k in ['access denied', '403 forbidden', 'cloudflare', 'attention required']):
        status = "blocked – bot protection (HTTP 403)"
    else:
        status = "no webcast link found"
        
    print(f"[{ticker}] RESULT => URL: {webcast_url} | Source: {url_source} | Status: {status} | HTTP: {http_status} | Inputs: {form_inputs_count} | Media: {len(media_captured)}")
    
    context.close()
    return {
        'ticker': ticker,
        'webcast_url': webcast_url,
        'url_source': url_source,
        'status': status,
        'http_status': http_status
    }

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--disable-http2'])
    for ticker in ['AAPL', 'JNJ', 'XOM', 'WMT', 'GOOGL', 'TSLA', 'PG', 'LLY', 'APT', 'DMRC', 'RELL', 'PESI', 'RY', 'ENB', 'ABX', 'T', 'NTR', 'MRU']:
        inspect_ticker(p, browser, ticker)
    browser.close()
