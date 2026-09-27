import re
from src.utils.rate_limiter import polite_get

txt = polite_get("https://www.apple.com/v/investor/earnings-call/d/built/scripts/main.built.js").text
print("Occurrences of events-delivery:", re.findall(r"https://events-delivery\.apple\.com[^\s\"\'<>]*", txt))
print("Occurrences of m3u8 or mp4:", re.findall(r"[^\s\"\'<>]+\.(?:m3u8|mp4|m4a|mp3)", txt))

# Look for m3u8 patterns
m3u8_matches = re.findall(r'["\']([^"\']+\.m3u8[^"\']*)["\']', txt)
print("m3u8 matches:", m3u8_matches)

# Look for vod or hls
vod_matches = re.findall(r'["\']([^"\']*(?:vod|hls|audio|stream)[^"\']*)["\']', txt)
print("vod/hls/audio/stream strings:", [v for v in vod_matches if len(v) < 150][:15])
