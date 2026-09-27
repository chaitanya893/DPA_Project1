# Corporate Earnings Call Pipeline – Audio Capture Setup & Technical Architecture

**Pipeline Phase:** Phase 2 (Audio Capture & Media Stream Ingestion)  
**Standard Audio Format:** WAV, 16,000 Hz Sampling Rate, 1 Channel (Mono), 16-bit Signed Linear PCM (`pcm_s16le`)  
**Ingested Dataset:** 12 full corporate earnings calls meeting Phase 2 validation requirements.

---

## 1. Supported Vendor Parsers

The automated audio capture pipeline employs dedicated, modular vendor parsers to extract direct master HLS stream endpoints (`.m3u8`) without requiring user interaction or authentication:

### A. Microsoft Medius Player Parser (`src/capture/msft_parser.py`)
- **Applies to**: Recent Microsoft quarters (e.g., FY2026 Q1–Q4, FY2025 Q4/Q1, FY2024 Q3/Q2).
- **Architecture**:
  1. Inspects the static HTML of the investor event page (`https://www.microsoft.com/en-us/investor/events/...`) to extract the embedded iframe source (`https://medius.microsoft.com/Embed/video-nc/<id>`) and the official transcript URL (`aka.ms/transcript...` or `.docx`).
  2. Launches headless Playwright Chromium (`--disable-http2`, `--autoplay-policy=no-user-gesture-required`).
  3. Navigates directly to the Medius iframe, simulates clicking the center of the video viewport, and triggers a muted JavaScript `video.play()` fallback.
  4. Intercepts network responses and queries `performance.getEntriesByType('resource')` to capture the `/master.m3u8` manifest hosted on `stream.event.microsoft.com`.

### B. Microsoft Mediastream JSON Config Parser (`src/capture/msft_parser.py`)
- **Applies to**: Older Microsoft quarters using the mediastream player (e.g., FY2025 Q3, FY2025 Q2).
- **Architecture**:
  1. Extracts the player URL: `https://mediastream.microsoft.com/events/players/live/player.html?path=<path>.json`.
  2. Directly fetches the JSON configuration endpoint defined in the `path` parameter.
  3. Recursively parses the JSON payload to extract `hostName` (`https://stream.event.microsoft.com/prodwe`) and the relative `manifest` path (`/Content/HLS/LLCU/.../master.m3u8`).
  4. Assembles the direct master HLS URL without browser overhead.

### C. Shopify Mux Player Parser (`src/capture/shopify_parser.py`)
- **Applies to**: Shopify investor earnings webcasts (e.g., `https://www.shopify.com/investors/quarterly-results/webcast/q2-2026`).
- **Architecture**:
  1. Navigates to the Shopify quarterly results webcast page.
  2. Attaches Playwright network listeners to intercept requests to `stream.mux.com`.
  3. Captures the high-fidelity HLS stream: `https://stream.mux.com/<mux_asset_id>.m3u8?redundant_streams=true`.
  4. Returns HTTP 404 cleanly for expired older quarters where the page no longer exists.

---

## 2. Ingestion & Audio Standardization Commands

All captured streams are downloaded and standardized using `ffmpeg` and `yt-dlp` into uniform linear PCM WAV files:

### Primary FFmpeg Extraction Command:
```bash
ffmpeg -y \
  -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
  -reconnect 1 \
  -reconnect_streamed 1 \
  -reconnect_delay_max 5 \
  -i "<STREAM_URL>" \
  -vn \
  -ar 16000 \
  -ac 1 \
  -c:a pcm_s16le \
  "data/audio/<TICKER>_<FISCAL_PERIOD>.wav"
```

### High-Throughput Stream Copy & Local Standardization:
For dynamic HLS manifests containing dedicated audio tracks (`Stream(08)/index.m3u8`), the stream is copied directly at network speed (25x–35x real-time) and converted locally:
```bash
# Step 1: Rapid stream copy
ffmpeg -y -user_agent "..." -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 \
  -i "<AUDIO_SUBSTREAM_URL>" -c copy "temp_audio.m4a"

# Step 2: Standardization to 16 kHz Mono 16-bit PCM WAV
ffmpeg -y -i "temp_audio.m4a" -vn -ar 16000 -ac 1 -c:a pcm_s16le "data/audio/<OUTPUT>.wav"
```

---

## 3. Strict Audio Validation Gates

Every audio file must satisfy all Phase 2 acceptance criteria before being admitted to `data/audio/capture_manifest.csv`:

1. **Duration Window**: Duration must be between **20 minutes** ($1,200\text{ s}$) and **3 hours** ($10,800\text{ s}$). Files outside this range are rejected.
2. **Sampling Rate & Channels**: Exactly **16,000 Hz**, single channel (**mono**).
3. **Bit Depth**: Exactly **16-bit** signed linear PCM (`pcm_s16le`).
4. **File Size**: Minimum **35 MB** uncompressed PCM payload ($1,200\text{ s} \times 32,000\text{ B/s} \approx 38.4\text{ MB}$).
5. **Novelty & SHA-256 Integrity**: Unique SHA-256 hash per call; verified zero overlap with synthetic test datasets in `data/_old_runs/`.
6. **Domain & Stream Compliance**:
   - Extraction from `youtube.com` / `youtu.be` is strictly forbidden.
   - Continuous unbounded live/DVR streams (e.g. event 34) are rejected.
   - Registration forms and login screens are never submitted.

---

## 4. Manifest Schema & 1:1 Mapping Guarantee

`data/audio/capture_manifest.csv` conforms to the canonical schema:
```csv
event_id,ticker,fiscal_period,audio_path,capture_mode,started_at,ended_at,duration_sec,sample_rate,file_size,sha256,failure_reason,source_url,replay_expiry_date,url_located_by
```

- **Exact 1:1 Mapping**: Every `.wav` file in `data/audio/` maps to exactly one row in `capture_manifest.csv`, and every valid manifest row maps to exactly one existing audio file.
- **Immediate Write**: Manifest updates occur immediately upon verification of each individual call.
