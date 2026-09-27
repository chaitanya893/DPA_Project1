import json, re

def check_file_exact(fpath, label):
    with open('data/cache/' + fpath, 'r', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
    content = data.get('content', '') or data.get('text', '') or data.get('html', '') or ''
    print(f"\n=================== {label} ({fpath}) ===================")
    for m in re.finditer(r'(webcast|conference call|listen)', content, re.IGNORECASE):
        s = max(0, m.start() - 100)
        e = min(len(content), m.end() + 250)
        print("RAW CHUNK:", content[s:e])

check_file_exact('0ab6e2ac036bab64ae32f7de4e9ed997efe830bfec47f41a442b6c74c404b7d0.json', 'GOOGL')
check_file_exact('cb4ed663be05cc6a15dee9904d0e98ff82175d493b3834b3c2db41f8329c7dc6.json', 'TSLA')
check_file_exact('7ffb9b4005646078a72d7037830c559e1495258e172f85981da898927f91497d.json', 'DMRC')
check_file_exact('404c99034fbf9d80c68d053812973a1cfad434b108f24996963efbc89d4c9175.json', 'RY')
