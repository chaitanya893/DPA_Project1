import json, re

def check_file(fpath, label):
    with open('data/cache/' + fpath, 'r', encoding='utf-8', errors='ignore') as f:
        data = json.load(f)
    content = data.get('content', '') or data.get('text', '') or data.get('html', '') or ''
    print(f"\n=================== {label} ({fpath}) ===================")
    # Search for webcast/audio/call
    for match in re.finditer(r'(webcast|conference call|listen live|audio replay|broadcast)', content, re.IGNORECASE):
        start = max(0, match.start() - 150)
        end = min(len(content), match.end() + 350)
        snippet = content[start:end]
        # Clean HTML slightly for readability
        snippet = re.sub(r'<[^>]+>', ' ', snippet)
        snippet = re.sub(r'\s+', ' ', snippet)
        print(f"--- Snippet:\n{snippet}\n")

# GOOGL
check_file('0ab6e2ac036bab64ae32f7de4e9ed997efe830bfec47f41a442b6c74c404b7d0.json', 'GOOGL')
# TSLA
check_file('cb4ed663be05cc6a15dee9904d0e98ff82175d493b3834b3c2db41f8329c7dc6.json', 'TSLA')
# DMRC
check_file('7ffb9b4005646078a72d7037830c559e1495258e172f85981da898927f91497d.json', 'DMRC')
# PESI
check_file('11cd6f222298a05a63c058331111760e2d4da7263a2bfd7781af3f5db93ad065.json', 'PESI')
# RY
check_file('404c99034fbf9d80c68d053812973a1cfad434b108f24996963efbc89d4c9175.json', 'RY')
