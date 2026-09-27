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

for ticker in target_18:
    row = universe[universe['ticker'] == ticker].iloc[0]
    name = row['company_name']
    cik = str(row.get('sec_cik', ''))
    ir_url = row['ir_page_url']
    
    print(f"\n=======================================================")
    print(f"TICKER: {ticker} | COMPANY: {name} | IR_URL: {ir_url}")
    print(f"=======================================================")
    
    found_in_cache = False
    for fpath, url, content in docs:
        is_match = False
        if cik and (f"/{cik}/" in url or f"data/{cik}" in url):
            is_match = True
        elif ticker in url or ticker.lower() in url.lower():
            is_match = True
        elif name.lower() in content[:1000].lower():
            is_match = True
            
        if is_match:
            # Check if this document is an earnings release or mentions webcast
            if any(k in content.lower() for k in ['earnings release', 'ex-99.1', 'results for', 'financial results', 'webcast', 'conference call']):
                # Find all URLs in content
                urls = re.findall(r'https?://[^\s<>"\'\)]+', content)
                # Find sentences with webcast
                paras = re.split(r'\n{2,}|\.\s+', content)
                for p in paras:
                    if any(w in p.lower() for w in ['webcast', 'conference call', 'listen', 'broadcast', 'audio replay']):
                        clean_p = re.sub(r'<[^>]+>', ' ', p).strip()
                        clean_p = re.sub(r'\s+', ' ', clean_p)
                        if len(clean_p) > 20:
                            print(f"  [Found in {os.path.basename(fpath)}]:")
                            print(f"    {clean_p[:300]}")
                            p_urls = re.findall(r'https?://[^\s<>"\'\)]+', p)
                            if p_urls:
                                print(f"    URLs: {p_urls}")
                            found_in_cache = True

