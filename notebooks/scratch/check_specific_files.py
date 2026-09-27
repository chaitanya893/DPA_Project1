import json, re

files = {
    'ENB': '228c0bd6dc2a117ef24cd811fb83b29b6602697800318a793c77f2cf85dc8a59.json',
    'LLY': '0d86720d639592ac2ebbabd7f15b06c4adb5b6a53127d379d8cd5f9495d60009.json',
    'RELL': '4320421eb5c0638784ec667eb05df16bf638dfccdbd9c5ae8bc9ddb0996045c3.json',
    'AAPL': '052ffe8266f1b8e513385d6c52dbffc9e43ac65496a75cea9a590ca8d454de5c.json',
    'WMT': '1ab00ac94d5d204f508bfc7ef45b1e8e962de7cd7b15ea0ab2647edf5cf844d2.json',
    'DMRC': '47a354b80886c776f04d9e86aaa1b737d82e1b2541b419018b50e0bb8c8bffc8.json'
}

for ticker, fname in files.items():
    with open('data/cache/' + fname, 'r', encoding='utf-8', errors='ignore') as fp:
        data = json.load(fp)
    c = data.get('content', '') or data.get('text', '') or data.get('html', '') or ''
    print(f"\n=================== {ticker} ({fname}) ===================")
    for m in re.finditer(r'(webcast|conference call|listen)', c, re.IGNORECASE):
        s = max(0, m.start() - 100)
        e = min(len(c), m.end() + 300)
        print("---")
        snip = re.sub(r'<[^>]+>', ' ', c[s:e])
        print(re.sub(r'\s+', ' ', snip).strip())
        urls = re.findall(r'https?://[^\s<>"\'\)]+', c[s:e])
        if urls:
            print("  Found URLs:", urls)
