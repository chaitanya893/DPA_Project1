import os
import json
import re
import pandas as pd

universe = pd.read_csv('config/universe.csv')
print("Universe tickers:", universe['ticker'].tolist())

cache_dir = 'data/cache'
cached_files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.json')]

target_tickers = [
    'AAPL', 'JNJ', 'XOM', 'WMT', 'GOOGL', 'TSLA', 'PG', 'LLY', 
    'APT', 'DMRC', 'RELL', 'PESI', 'RY', 'ENB', 'ABX', 'T', 'NTR', 'MRU'
]

print(f"Total cache files: {len(cached_files)}")

# Let's inspect each cached file
file_data = []
for fpath in cached_files:
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            file_data.append((fpath, data))
    except Exception as e:
        pass

print(f"Loaded {len(file_data)} JSON cache entries.")

for ticker in target_tickers:
    t_row = universe[universe['ticker'] == ticker].iloc[0]
    cname = t_row['company_name']
    cik = str(t_row.get('cik', ''))
    
    print(f"\n=================== {ticker} ({cname}) ===================")
    found_any = False
    for fpath, data in file_data:
        url = data.get('url', '')
        content = str(data.get('content', '') or data.get('text', '') or data.get('body', '') or data.get('html', ''))
        
        # Check if relevant to this ticker
        ticker_match = (
            ticker in url or 
            (cik and cik in url) or 
            ticker.lower() in url.lower() or 
            (ticker in content and ('press release' in content.lower() or 'ex-99' in content.lower() or 'webcast' in content.lower() or 'earnings' in content.lower()))
        )
        
        if ticker_match and ('webcast' in content.lower() or 'conference call' in content.lower() or 'broadcast' in content.lower()):
            print(f"\n--- Cache file: {os.path.basename(fpath)} | URL: {url[:100]} ---")
            
            # Find paragraphs/sentences containing 'webcast' or 'conference call' or 'listen' or 'replay'
            lines = content.split('\n')
            for line in lines:
                if any(w in line.lower() for w in ['webcast', 'conference call', 'listen', 'replay', 'audio stream']):
                    # Clean tags
                    clean_line = re.sub(r'<[^>]+>', ' ', line).strip()
                    if len(clean_line) > 10:
                        print(f"  [Context]: {clean_line[:200]}")
                        # Find URLs in this line or nearby
                        urls = re.findall(r'https?://[^\s<>"\']+', line)
                        for u in urls:
                            print(f"    --> URL: {u}")
            found_any = True

