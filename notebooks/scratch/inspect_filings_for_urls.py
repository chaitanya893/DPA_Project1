import os, json, re
import pandas as pd

universe = pd.read_csv('config/universe.csv')
cache_dir = 'data/cache'

files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.json')]
docs = []
for f in files:
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            data = json.load(fp)
            docs.append((f, data.get('url', ''), data.get('content', '') or data.get('text', '') or data.get('html', '') or ''))
    except:
        pass

target_18 = ['AAPL', 'JNJ', 'XOM', 'WMT', 'GOOGL', 'TSLA', 'PG', 'LLY', 'APT', 'DMRC', 'RELL', 'PESI', 'RY', 'ENB', 'ABX', 'T', 'NTR', 'MRU']

for ticker in target_18:
    row = universe[universe['ticker'] == ticker].iloc[0]
    name = row['company_name']
    cik = str(row.get('sec_cik', ''))
    
    found_urls = []
    for fpath, url, content in docs:
        is_match = False
        if cik and cik != 'NONE' and cik != 'nan' and (f"/{cik}/" in url or f"data/{cik}" in url):
            is_match = True
        elif ticker.lower() in url.lower():
            is_match = True
        elif name.lower() in content[:1000].lower():
            is_match = True
            
        if is_match:
            # Look for webcast section
            paras = re.split(r'\n{2,}|\.\s+', content)
            for p in paras:
                if any(w in p.lower() for w in ['webcast', 'conference call', 'listen', 'broadcast', 'replay']):
                    clean_p = re.sub(r'<[^>]+>', ' ', p).strip()
                    urls = re.findall(r'https?://[^\s<>"\'\)]+', clean_p)
                    for u in urls:
                        found_urls.append((os.path.basename(fpath), u, clean_p[:150]))
                        
    print(f"[{ticker}] ({name}) => {len(found_urls)} URLs found in cache filings:")
    seen = set()
    for src, u, snip in found_urls:
        if u not in seen:
            seen.add(u)
            print(f"   -> {u} (from {src})\n      Snip: {snip}")
