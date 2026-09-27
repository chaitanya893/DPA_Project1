import json
import re
from bs4 import BeautifulSoup

def find_links_in_cache(fname, query):
    with open('data/cache/' + fname, 'r', encoding='utf-8', errors='ignore') as fp:
        c = json.load(fp).get('content', '')
    soup = BeautifulSoup(c, 'html.parser')
    print(f"=== Links in {fname} ===")
    for a in soup.find_all('a', href=True):
        t = a.get_text().strip()
        h = a['href']
        if any(w in t.lower() or w in h.lower() for w in ['webcast', 'here', 'conference', 'event', 'investor', 'q4', 'q3', 'q2', 'q1']):
            print(f"  Text: {t} -> {h}")

find_links_in_cache('4320421eb5c0638784ec667eb05df16bf638dfccdbd9c5ae8bc9ddb0996045c3.json', 'RELL')
find_links_in_cache('98256a8178dda801dc1f7f6092e08a7470cdbfe3031f035895ab5e5d1e94387c.json', 'JNJ')
find_links_in_cache('3ec985b8fae925925c4efc982cb74ea1ba81ce47b6bf314b9cb7ea12fc66c61f.json', 'XOM')
find_links_in_cache('f3b99011a463a371d468c71b2be1815d4cd2f0e065e2d30a69941df2ed96ba5b.json', 'WMT')
