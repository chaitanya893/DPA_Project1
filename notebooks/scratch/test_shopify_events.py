import requests
from bs4 import BeautifulSoup

url = "https://investors.shopify.com/events/default.aspx"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")
print("Shopify Events:")
for a in soup.find_all("a"):
    t = a.get_text().strip()
    h = a.get("href", "")
    if any(k in t.lower() for k in ["quarter", "earnings", "q1", "q2", "q3", "q4"]):
        print(f"  {t} -> {h}")
