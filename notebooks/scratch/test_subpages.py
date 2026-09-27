import re
from bs4 import BeautifulSoup
from src.utils.rate_limiter import polite_get

urls = [
    ("AAPL", "https://www.apple.com/investor/earnings-call/"),
    ("MSFT", "https://www.microsoft.com/en-us/Investor/earnings/detail.aspx"),
    ("JPM", "https://www.jpmorganchase.com/ir/quarterly-results/2026/2q26"),
    ("TSLA", "https://ir.tesla.com/press-release/tesla-q2-2026-financial-results-and-qa-webcast"),
    ("RY", "https://www.rbc.com/investor-relations/quarterly-results.html"),
    ("RELL", "https://rell.com/investor-relations/financial-information/quarterly-results/"),
    ("ATD", "https://corpo.couche-tard.com/en/investors/events-presentations/"),
    ("MRU", "https://corpo.metro.ca/en/investor-relations/quarterly-results.html"),
    ("ENB", "https://www.enbridge.com/investment-center/events-and-presentations"),
]

for t, u in urls:
    try:
        resp = polite_get(u)
        print(f"{t} ({u}): Status {resp.status_code}, len={len(resp.text)}")
        media = re.findall(r"https?://[^\s<>\"\'()]+\.(?:mp3|mp4|m4a|m3u8|wav)", resp.text, re.IGNORECASE)
        print(f"  Found media: {media[:3]}")
        
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.find_all("a"):
            h = a.get("href", "")
            if any(k in h.lower() for k in ["audio", "webcast", "listen", "replay", "mp3", "recording"]):
                links.append((a.get_text(strip=True), h))
        print(f"  Audio/webcast links: {links[:3]}")
    except Exception as e:
        print(f"{t}: Error {e}")
