import os, json, re

cache_dir = 'data/cache'
files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.json')]

tickers = ['AAPL', 'JNJ', 'XOM', 'WMT', 'PG', 'LLY', 'APT', 'RELL', 'ENB', 'ABX', 'T', 'NTR', 'MRU']

for t in tickers:
    print(f"\n=================== {t} ===================")
    found = 0
    for f in files:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            data = json.load(fp)
            c = data.get('content', '') or data.get('text', '') or data.get('html', '') or ''
            u = data.get('url', '')
            
            # Check if relevant
            if t in u or t.lower() in u.lower() or f'ticker={t}' in u.lower():
                pass
            elif t == 'AAPL' and 'apple' in c[:1000].lower() and 'ex-99' in c.lower():
                pass
            elif t == 'JNJ' and 'johnson & johnson' in c[:1000].lower() and ('earnings' in c.lower() or 'ex-99' in c.lower()):
                pass
            elif t == 'XOM' and 'exxon' in c[:1000].lower() and ('earnings' in c.lower() or 'ex-99' in c.lower()):
                pass
            elif t == 'WMT' and 'walmart' in c[:1000].lower() and ('earnings' in c.lower() or 'ex-99' in c.lower()):
                pass
            elif t == 'PG' and 'procter' in c[:1000].lower() and ('earnings' in c.lower() or 'ex-99' in c.lower()):
                pass
            elif t == 'LLY' and 'eli lilly' in c[:1000].lower() and ('earnings' in c.lower() or 'ex-99' in c.lower()):
                pass
            elif t == 'APT' and 'alpha pro tech' in c[:1000].lower():
                pass
            elif t == 'RELL' and 'richardson electronics' in c[:1000].lower():
                pass
            elif t == 'ENB' and 'enbridge' in c[:1000].lower():
                pass
            elif t == 'ABX' and 'barrick' in c[:1000].lower():
                pass
            elif t == 'T' and 'telus' in c[:1000].lower():
                pass
            elif t == 'NTR' and 'nutrien' in c[:1000].lower():
                pass
            elif t == 'MRU' and 'metro inc' in c[:1000].lower():
                pass
            else:
                continue
                
            # Search for webcast or press release URL
            print(f"File: {os.path.basename(f)} | URL: {u}")
            for m in re.finditer(r'(webcast|conference call|listen|broadcast|audio|replay)', c, re.IGNORECASE):
                s = max(0, m.start() - 100)
                e = min(len(c), m.end() + 200)
                snip = re.sub(r'<[^>]+>', ' ', c[s:e])
                snip = re.sub(r'\s+', ' ', snip).strip()
                if len(snip) > 20:
                    print(f"   -> {snip}")
            found += 1
            if found >= 3:
                break
