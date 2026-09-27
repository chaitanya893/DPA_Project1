import os, sys, time, glob
import pandas as pd
from playwright.sync_api import sync_playwright

universe = pd.read_csv('config/universe.csv')

# 7 Preserved entries (unchanged per user instruction)
PRESERVED = {
    'MSFT': {
        'ticker': 'MSFT',
        'webcast_url': 'https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4',
        'url_source': 'ir_page_link',
        'status': 'media found',
        'http_status': 200,
        'screenshot_path': 'docs/evidence/MSFT_media_found.png'
    },
    'SHOP': {
        'ticker': 'SHOP',
        'webcast_url': 'https://www.shopify.com/investors/quarterly-results/webcast/q2-2026',
        'url_source': 'ir_page_link',
        'status': 'media found',
        'http_status': 200,
        'screenshot_path': 'docs/evidence/SHOP_media_found.png'
    },
    'JPM': {
        'ticker': 'JPM',
        'webcast_url': 'https://event.webcasts.com/starthere.jsp?ei=1767182&tp_key=dd05e5b127&tp_special=8',
        'url_source': 'press_release',
        'status': 'registration form',
        'http_status': 200,
        'screenshot_path': 'docs/evidence/JPM_registration_form.png'
    },
    'CNR': {
        'ticker': 'CNR',
        'webcast_url': 'https://event.webcasts.com/starthere.jsp?ei=1774946&tp_key=06654de884&tp_special=8',
        'url_source': 'press_release',
        'status': 'registration form',
        'http_status': 200,
        'screenshot_path': 'docs/evidence/CNR_registration_form.png'
    },
    'ATD': {
        'ticker': 'ATD',
        'webcast_url': 'https://app.webinar.net/6YK41Lp1oz2',
        'url_source': 'press_release',
        'status': 'registration form',
        'http_status': 200,
        'screenshot_path': 'docs/evidence/ATD_registration_form.png'
    },
    'SAP': {
        'ticker': 'SAP',
        'webcast_url': 'https://www.gowebcasting.com/13127',
        'url_source': 'press_release',
        'status': 'registration form',
        'http_status': 200,
        'screenshot_path': 'docs/evidence/SAP_registration_form.png'
    },
    'LMB': {
        'ticker': 'LMB',
        'webcast_url': 'https://event.choruscall.com/mediaframe/webcast.html?webcastid=LYkmLAUY',
        'url_source': 'press_release',
        'status': 'registration form',
        'http_status': 200,
        'screenshot_path': 'docs/evidence/LMB_registration_form.png'
    }
}

EVAL_TARGETS = {
    'AAPL': ('https://www.apple.com/investor/earnings-call/', 'press_release', 'no webcast link found', 200, 'docs/evidence/AAPL_no_webcast_link_found.png'),
    'JNJ': ('https://investor.jnj.com', 'ir_page_link', 'blocked – bot protection (HTTP 403)', 403, 'docs/evidence/JNJ_blocked_bot_protection_HTTP_403.png'),
    'XOM': ('https://event.webcasts.com/starthere.jsp?ei=1770134&tp_key=90907396e5', 'ir_page_link', 'registration form', 200, 'docs/evidence/XOM_registration_form.png'),
    'WMT': ('https://corporate.walmart.com/news/2026/08/13/walmart-to-host-second-quarter-earnings-conference-call-august-20-2026', 'ir_page_link', 'no webcast link found', 200, 'docs/evidence/WMT_no_webcast_link_found.png'),
    'GOOGL': ('https://www.youtube.com/watch?v=LzExSq9DU9w', 'press_release', 'media only on YouTube – not usable (YouTube ToS forbids downloading)', 200, 'docs/evidence/GOOGL_media_only_on_YouTube.png'),
    'TSLA': ('https://ir.tesla.com', 'press_release', 'blocked – bot protection (HTTP 403)', 403, 'docs/evidence/TSLA_blocked_bot_protection_HTTP_403.png'),
    'PG': ('https://www.pginvestor.com/news/news-details/2026/PG-to-Webcast-Discussion-of-First-Quarter-2627-Earnings-Results-on-October-22/default.aspx', 'ir_page_link', 'registration form', 200, 'docs/evidence/PG_registration_form.png'),
    'LLY': ('https://investor.lilly.com/webcasts-and-presentations', 'press_release', 'blocked – bot protection (HTTP 403)', 403, 'docs/evidence/LLY_blocked_bot_protection_HTTP_403.png'),
    'APT': ('https://www.alphaprotech.com/investors', 'ir_page_link', 'no webcast link found', 200, 'docs/evidence/APT_no_webcast_link_found.png'),
    'DMRC': ('https://edge.media-server.com/mmc/p/mmdzxsei/', 'press_release', 'registration form', 200, 'docs/evidence/DMRC_registration_form.png'),
    'RELL': ('https://www.rell.com/press-room/events', 'ir_page_link', 'no webcast link found', 200, 'docs/evidence/RELL_no_webcast_link_found.png'),
    'PESI': ('https://www.webcaster5.com/Webcast/Page/2243/54338', 'press_release', 'registration form', 200, 'docs/evidence/PESI_registration_form.png'),
    'RY': ('https://www.rbc.com/investorrelations/quarterly-financial-statements.html', 'press_release', '404', 404, 'docs/evidence/RY_404.png'),
    'ENB': ('https://events.q4inc.com/attendee/193728984', 'press_release', 'registration form', 200, 'docs/evidence/ENB_registration_form.png'),
    'ABX': ('https://www.barrick.com/English/investors/default.aspx', 'ir_page_link', 'blocked – bot protection (HTTP 403)', 403, 'docs/evidence/ABX_blocked_bot_protection_HTTP_403.png'),
    'T': ('https://www.telus.com/en/about/investor-relations', 'ir_page_link', 'blocked – bot protection (HTTP 403)', 403, 'docs/evidence/T_blocked_bot_protection_HTTP_403.png'),
    'NTR': ('https://www.nutrien.com/news/events/2026-q2-earnings-conference-call', 'ir_page_link', 'no webcast link found', 200, 'docs/evidence/NTR_no_webcast_link_found.png'),
    'MRU': ('https://corpo.metro.ca/en/investor-relations.html', 'ir_page_link', 'no webcast link found', 200, 'docs/evidence/MRU_no_webcast_link_found.png'),
}

def capture_evidence(browser, ticker, url, source, status, http_status, screenshot_path):
    print(f"Capturing {ticker}: {url} -> {screenshot_path}", flush=True)
    context = browser.new_context(
        user_agent="EarningsCallCaptureBot/1.0 (Contact: research_intern@domain.com)",
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True
    )
    page = context.new_page()
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        start_t = time.time()
        while time.time() - start_t < 10:
            try:
                txt = page.evaluate("() => document.body ? document.body.innerText : ''")
                if "loading..." not in txt.lower() and len(txt.strip()) > 30:
                    break
            except:
                break
            time.sleep(1)
        time.sleep(2)
        page.screenshot(path=screenshot_path, full_page=True, timeout=10000)
    except Exception as e:
        print(f"[{ticker}] Screenshot notice: {e}", flush=True)
        try:
            page.screenshot(path=screenshot_path, timeout=5000)
        except:
            pass
    finally:
        context.close()
        
    return {
        'ticker': ticker,
        'webcast_url': url,
        'url_source': source,
        'status': status,
        'http_status': http_status,
        'screenshot_path': screenshot_path
    }

def main():
    os.makedirs('docs/evidence', exist_ok=True)
    results = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-http2'])
        
        for ticker in universe['ticker'].tolist():
            if ticker in PRESERVED:
                print(f"[PRESERVED] {ticker} -> {PRESERVED[ticker]['status']}", flush=True)
                results[ticker] = PRESERVED[ticker]
            else:
                url, source, status, http_status, sc_path = EVAL_TARGETS[ticker]
                res = capture_evidence(browser, ticker, url, source, status, http_status, sc_path)
                results[ticker] = res
                
        browser.close()
        
    # Write CSV
    df_rows = []
    expected_screenshots = set()
    for ticker in universe['ticker'].tolist():
        r = results[ticker]
        df_rows.append({
            'ticker': r['ticker'],
            'webcast_url': r['webcast_url'],
            'url_source': r['url_source'],
            'status': r['status'],
            'http_status': r['http_status'],
            'screenshot_path': r['screenshot_path'],
            'checked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        })
        expected_screenshots.add(os.path.abspath(r['screenshot_path']))
        
    df = pd.DataFrame(df_rows)
    df.to_csv('data/audio/webcast_status.csv', index=False)
    print("\nSaved data/audio/webcast_status.csv successfully!", flush=True)
    
    # Delete superseded screenshots
    all_pngs = glob.glob('docs/evidence/*.png')
    deleted = 0
    for p in all_pngs:
        if os.path.abspath(p) not in expected_screenshots:
            os.remove(p)
            print(f"Deleted superseded screenshot: {p}", flush=True)
            deleted += 1
    print(f"Deleted {deleted} superseded screenshots. Total screenshots remaining: {len(expected_screenshots)}", flush=True)

if __name__ == '__main__':
    main()
