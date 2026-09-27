import os, json, re
import pandas as pd
from bs4 import BeautifulSoup

universe = pd.read_csv('config/universe.csv')
cache_dir = 'data/cache'

files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith('.json')]
print(f"Total cache files: {len(files)}")

docs = []
for f in files:
    try:
        with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
            data = json.load(fp)
            docs.append({
                'fpath': f,
                'url': data.get('url', ''),
                'content': data.get('content', '') or data.get('text', '') or data.get('html', '') or ''
            })
    except:
        pass

print(f"Loaded {len(docs)} cache docs.")

tickers = ['AAPL', 'JNJ', 'XOM', 'WMT', 'GOOGL', 'TSLA', 'PG', 'LLY', 'APT', 'DMRC', 'RELL', 'PESI', 'RY', 'ENB', 'ABX', 'T', 'NTR', 'MRU']

company_keywords = {
    'AAPL': ['apple inc', 'aapl', '0000320193', '320193'],
    'JNJ': ['johnson & johnson', 'jnj', '0000200406', '200406'],
    'XOM': ['exxon mobil', 'exxonmobil', 'xom', '0000034088', '34088'],
    'WMT': ['walmart', 'wmt', '0000104169', '104169'],
    'GOOGL': ['alphabet inc', 'google', 'googl', '0001652044', '1652044'],
    'TSLA': ['tesla, inc', 'tesla inc', 'tsla', '0001318605', '1318605'],
    'PG': ['procter & gamble', 'pginvestor', '0000080424', '80424'],
    'LLY': ['eli lilly', 'lilly', 'lly', '0000059478', '59478'],
    'APT': ['alpha pro tech', 'apt', '0000884269', '884269'],
    'DMRC': ['digimarc', 'dmrc', '0001438231', '1438231'],
    'RELL': ['richardson electronics', 'rell', '0000355948', '355948'],
    'PESI': ['perma-fix', 'pesi', '0000891532', '891532'],
    'RY': ['royal bank of canada', 'rbc', '0001000275', '1000275'],
    'ENB': ['enbridge', 'enb', '0000895728', '895728'],
    'ABX': ['barrick gold', 'barrick', 'abx', '0000756894', '756894'],
    'T': ['telus corp', 'telus', '0000868675', '868675'],
    'NTR': ['nutrien', 'ntr', '0001725964', '1725964'],
    'MRU': ['metro inc', 'mru', '0002073643', '2073643']
}

for ticker in tickers:
    kw_list = company_keywords[ticker]
    print(f"\n=======================================================")
    print(f"TICKER: {ticker}")
    print(f"=======================================================")
    
    found_count = 0
    for d in docs:
        u = d['url'].lower()
        c = d['content']
        c_lower = c.lower()
        
        # Check if matched
        if any(kw in u for kw in kw_list) or (any(kw in c_lower[:1000] for kw in kw_list) and any(w in c_lower for w in ['results', 'earnings', 'quarter', 'financial'])):
            # Look for webcast section
            if any(w in c_lower for w in ['webcast', 'conference call', 'listen live', 'audio stream', 'replay']):
                soup = BeautifulSoup(c, 'html.parser')
                text = soup.get_text(separator=' ')
                
                # Look for paragraph mentioning webcast
                sentences = re.split(r'[\r\n]+|\.\s+', text)
                webcast_sentences = []
                for s in sentences:
                    if any(w in s.lower() for w in ['webcast', 'conference call', 'listen', 'broadcast', 'replay']):
                        clean_s = re.sub(r'\s+', ' ', s).strip()
                        if len(clean_s) > 20:
                            webcast_sentences.append(clean_s)
                
                # Look for links
                links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    t = a.get_text().strip()
                    if any(w in t.lower() or w in href.lower() for w in ['webcast', 'conference', 'listen', 'event', 'audio', 'q4inc', 'choruscall', 'webinar', 'webcasts']):
                        links.append((t, href))
                        
                print(f"File: {os.path.basename(d['fpath'])} | URL: {d['url']}")
                if webcast_sentences:
                    print(f"  Webcast Text: {webcast_sentences[0][:200]}")
                if links:
                    print(f"  Links: {links[:3]}")
                found_count += 1
                if found_count >= 2:
                    break
    if found_count == 0:
        print("  (No cached press release with webcast found)")
