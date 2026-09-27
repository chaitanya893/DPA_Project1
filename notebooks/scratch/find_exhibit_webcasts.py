import re
from src.discovery.sec_edgar import fetch_sec_submissions, find_all_exhibit_urls
from src.utils.rate_limiter import polite_get
from src.db.session import SessionLocal
from src.db.models import CompanyUniverse

db = SessionLocal()
comps = [(c.ticker, c.cik_or_sedar_id, c.country) for c in db.query(CompanyUniverse).all()]
db.close()

for ticker, cik, country in comps:
    if cik and cik.replace('0','').isdigit():
        sub = fetch_sec_submissions(cik)
        if sub:
            recent = sub.get('filings', {}).get('recent', {})
            forms = recent.get('form', [])
            accs = recent.get('accessionNumber', [])
            for f, a in zip(forms, accs):
                if f in ['8-K', '6-K']:
                    ex_urls = find_all_exhibit_urls(cik, a.replace('-',''))
                    for eu in ex_urls[:3]:
                        txt = polite_get(eu).text
                        links = re.findall(r'https?://[^\s<>"\'()]+', txt)
                        media_links = [l.rstrip('.,;)\"') for l in links if any(k in l.lower() for k in ['q4', 'notified', 'webcast', 'on24', 'choruscall', 'viavid', 'event', 'audio', 'broadcast', 'investor', 'stream'])]
                        if media_links:
                            print(f"{ticker} ({f} {a}):", media_links[:3])
                    break
