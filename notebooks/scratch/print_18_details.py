import os
import json
import re
import pandas as pd

universe = pd.read_csv('config/universe.csv')
cache_dir = 'data/cache'

files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.json')]
docs = []
for f in files:
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            data = json.load(fp)
            url = data.get('url', '')
            content = data.get('content', '') or data.get('text', '') or data.get('html', '') or ''
            docs.append((f, url, content))
    except:
        pass

target_18 = ['AAPL', 'JNJ', 'XOM', 'WMT', 'GOOGL', 'TSLA', 'PG', 'LLY', 'APT', 'DMRC', 'RELL', 'PESI', 'RY', 'ENB', 'ABX', 'T', 'NTR', 'MRU']

found_info = {}

for ticker in target_18:
    row = universe[universe['ticker'] == ticker].iloc[0]
    name = row['company_name']
    cik = str(row.get('sec_cik', ''))
    ir_url = row['ir_page_url']
    
    found_info[ticker] = []
    
    for fpath, url, content in docs:
        is_match = False
        if cik and cik != 'NONE' and cik != 'nan' and (f"/{cik}/" in url or f"data/{cik}" in url):
            is_match = True
        elif ticker.lower() in url.lower():
            is_match = True
        elif name.lower() in content[:1000].lower():
            is_match = True
            
        if is_match:
            # Look for webcast URLs
            paras = re.split(r'\n{2,}|\.\s+', content)
            for p in paras:
                if any(w in p.lower() for w in ['webcast', 'conference call', 'listen', 'broadcast', 'audio replay', 'financial results']):
                    # Check if there is a URL
                    urls = re.findall(r'https?://[^\s<>"\'\)]+', p)
                    clean_p = re.sub(r'<[^>]+>', ' ', p).strip()
                    clean_p = re.sub(r'\s+', ' ', clean_p)
                    if urls or 'webcast' in p.lower():
                        found_info[ticker].append({
                            'source': os.path.basename(fpath),
                            'text': clean_p[:200],
                            'urls': urls
                        })

for ticker in target_18:
    print(f"=== {ticker} ({len(found_info[ticker])} hits) ===")
    seen = set()
    for item in found_info[ticker]:
        txt = item['text']
        if txt not in seen:
            seen.add(txt)
            print(f"  [{item['source']}] {txt}")
            if item['urls']:
                print(f"    URLs: {item['urls']}")
