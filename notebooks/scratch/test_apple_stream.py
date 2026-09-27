import re
from src.utils.rate_limiter import polite_get

html = polite_get("https://www.apple.com/investor/earnings-call/").text
scripts = re.findall(r'src="([^"]+\.js)"', html)
print("Scripts on Apple earnings page:", len(scripts))
for s in scripts:
    u = f"https://www.apple.com{s}" if s.startswith("/") else s
    txt = polite_get(u).text
    matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', txt)
    if matches:
        print(f"Found m3u8 in {s}:", matches)
    else:
        # Check for akamai or events streams
        streams = re.findall(r'https?://[^\s"\'<>]*(?:events|stream|delivery|podcast)[^\s"\'<>]*', txt)
        if streams:
            print(f"Potential streams in {s}:", streams[:3])
