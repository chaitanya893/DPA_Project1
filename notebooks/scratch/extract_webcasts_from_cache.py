import os
import json
import re
import pandas as pd
from bs4 import BeautifulSoup

universe = pd.read_csv('config/universe.csv')

cache_dir = 'data/cache'
cached_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.json')]

all_records = []
for fpath in cached_files:
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            url = data.get('url', '')
            content = data.get('content', '') or data.get('text', '') or data.get('html', '') or ''
            all_records.append({'fpath': fpath, 'url': url, 'content': content})
    except:
        pass

print(f"Loaded {len(all_records)} cache files.")

target_tickers = [
    'AAPL', 'JNJ', 'XOM', 'WMT', 'GOOGL', 'TSLA', 'PG', 'LLY', 
    'APT', 'DMRC', 'RELL', 'PESI', 'RY', 'ENB', 'ABX', 'T', 'NTR', 'MRU',
    'MSFT', 'SHOP', 'JPM', 'LMB', 'CNR', 'ATD', 'SAP'
]

results = {}

for ticker in target_tickers:
    t_row = universe[universe['ticker'] == ticker].iloc[0]
    cname = t_row['company_name']
    cik = str(t_row.get('cik', ''))
    ir_url = str(t_row.get('ir_url', ''))
    
    matches = []
    for r in all_records:
        u = r['url']
        c = r['content']
        
        # Determine if this record belongs to the ticker
        match = False
        if cik and f"data/{cik}" in u or f"/{cik}/" in u:
            match = True
        elif ticker.lower() in u.lower():
            match = True
        elif cname.lower() in c[:2000].lower() or ticker in c[:500]:
            match = True
            
        if match:
            # Look for webcast section
            soup = BeautifulSoup(c, 'html.parser')
            text = soup.get_text(separator=' ')
            
            # Find URLs
            # In HTML: look for <a> tags with webcast/listen/conference call text or href
            webcast_links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                link_text = a.get_text().strip().lower()
                href_lower = href.lower()
                if any(w in link_text or w in href_lower for w in ['webcast', 'conference', 'listen', 'audio', 'broadcast', 'event', 'replay', 'q1', 'q2', 'q3', 'q4']):
                    webcast_links.append((link_text, href))
            
            # Also regex search for plain text URLs near "webcast"
            text_urls = []
            for sentence in re.split(r'[\r\n\.]+', text):
                if any(k in sentence.lower() for k in ['webcast', 'conference call', 'listen', 'broadcast', 'audio']):
                    found = re.findall(r'https?://[^\s<>"\')]+', sentence)
                    for f in found:
                        text_urls.append((sentence.strip()[:100], f))
            
            if webcast_links or text_urls:
                matches.append({
                    'fpath': os.path.basename(r['fpath']),
                    'url': u,
                    'html_links': webcast_links,
                    'text_urls': text_urls,
                    'sample_text': text[:300]
                })
    results[ticker] = matches

for ticker, matches in results.items():
    print(f"\n=================== {ticker} ({len(matches)} filing matches) ===================")
    for m in matches[:5]:
        print(f"File: {m['fpath']} | Source URL: {m['url']}")
        if m['html_links']:
            print("  HTML Links:", m['html_links'][:5])
        if m['text_urls']:
            print("  Text URLs:", m['text_urls'][:5])
