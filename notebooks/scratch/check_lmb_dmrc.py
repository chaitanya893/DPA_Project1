import re
from src.utils.rate_limiter import polite_get
from bs4 import BeautifulSoup

for name, u in [
    ("LMB", "https://www.sec.gov/Archives/edgar/data/1606163/000160616326000028/lmb-20260805.htm"),
    ("DMRC", "https://www.sec.gov/Archives/edgar/data/1438231/000143774926016421/dmrc-ex99_1.htm")
]:
    txt = polite_get(u).text
    soup = BeautifulSoup(txt, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    domains = re.findall(r'[a-zA-Z0-9\.\-]+\.(?:com|org|net|io|ca)[a-zA-Z0-9/\.\-_]*', text)
    print(f"=== {name} Web Domains ===")
    for d in set(domains):
        print(" ", d)
