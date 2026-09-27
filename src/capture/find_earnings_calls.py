import json
import yt_dlp

queries = {
    'AAPL': 'Apple Financial Results - Q3 2024 earnings call',
    'MSFT': 'Microsoft Q3 2024 earnings conference call',
    'GOOGL': 'Alphabet Inc Q3 2024 Earnings Conference Call',
    'TSLA': 'Tesla Q3 2024 Financial Results and Q&A Webcast',
    'JPM': 'JPMorgan Chase Q3 2024 Earnings Conference Call',
    'XOM': 'Exxon Mobil 3Q 2024 Earnings Conference Call',
    'WMT': 'Walmart Inc. FY2025 Q3 Earnings Release webcast',
    'LMB': 'Limbach Holdings Q3 2024 Earnings Conference Call',
    'DMRC': 'Digimarc Corporation Q3 2024 Earnings Conference Call',
    'RELL': 'Richardson Electronics Q4 2024 Earnings Conference Call',
    'PESI': 'Perma-Fix Environmental Services Q3 2024 earnings call',
    'SHOP': 'Shopify Q3 2024 Financial Results Conference Call',
    'RY': 'Royal Bank of Canada Q3 2024 Results Conference Call',
    'CNR': 'Canadian National Railway Q3 2024 Financial Results Call',
    'ENB': 'Enbridge Inc Q3 2024 Financial Results Conference Call',
    'ATD': 'Alimentation Couche-Tard Q1 2025 Earnings Call Webcast',
    'MRU': 'Metro Inc Q3 2024 Results Conference Call',
    'SAP': 'Saputo Inc Q1 2025 Results Conference Call',
}

results = {}
ydl_opts = {'quiet': True, 'extract_flat': True}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for ticker, q in queries.items():
        try:
            res = ydl.extract_info(f'ytsearch3:{q}', download=False)
            entries = res.get('entries', [])
            results[ticker] = []
            for e in entries:
                results[ticker].append({
                    'title': e.get('title'),
                    'url': e.get('url'),
                    'duration': e.get('duration')
                })
        except Exception as err:
            results[ticker] = [{'error': str(err)}]

print(json.dumps(results, indent=2))
