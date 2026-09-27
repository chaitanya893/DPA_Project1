# Corporate Earnings Call Pipeline – Audio Capture Setup & Technical Architecture

**Pipeline Phase:** Phase 2 (Audio Capture & Media Stream Ingestion)  
**Standard Audio Format:** WAV, 16,000 Hz Sampling Rate, 1 Channel (Mono), 16-bit Signed Linear PCM (`pcm_s16le`)  
**Target Ingestion Target:** At least 12 full corporate earnings calls meeting the universe cohort specifications.

---

## 1. Supported Capture Modes & Hierarchy of Preference

In accordance with the project specification and compliance guidelines, the pipeline attempts capture modes in the following strict hierarchy:

| Mode ID | Capture Mode Name | Implementation Strategy & Mechanics | Operational Status |
| :--- | :--- | :--- | :--- |
| **Mode 1** | **Direct Media URL** | Headless Playwright (`chromium`) opens official webcast/IR event player, observes network requests for direct audio streams (`.m3u8` HLS, `.mp3`, `.mp4`, `.m4a`, `.aac`), and streams directly via `ffmpeg` or `yt-dlp`. | **Active (Primary)** |
| **Mode 2** | **Headless Browser Audio Sink** | Native virtual audio loopback sink capturing real-time WebRTC/HTML5 audio elements. | **Not available on this machine** (Windows environment requires third-party virtual audio driver like VB-Cable; direct media stream used instead). |
| **Mode 3** | **Archived Replay File Download** | Direct HTTP download of static archived `.mp3` / `.wav` media recordings published on issuer IR archives. | **Active (Fallback)** |

---

## 2. Environment Tools & Dependencies

All audio capture, network sniffing, and standardization tools are pinned and verified:

| Tool / Package | Version | Purpose |
| :--- | :--- | :--- |
| **FFmpeg** | `9.0.1` | Stream extraction, audio format conversion, resampling to 16 kHz mono 16-bit PCM. |
| **Playwright** | `1.63.0` | Headless Chromium browser automation for dynamic DOM rendering and network response interception. |
| **yt-dlp** | `2026.8.19` | Resilient HLS/m3u8 stream downloading for vendor webcast endpoints (excluding forbidden domains). |
| **BeautifulSoup4** | `4.12.0` | DOM parsing to detect registration forms, paywalls, and embedded media tags. |
| **Python** | `3.14.3` | Core pipeline orchestration runtime. |

---

## 3. Compliance & Governance Rules

1. **No YouTube Ingestion**: Direct extraction from `youtube.com` / `youtu.be` is strictly forbidden by project policy and Section 5.B of YouTube Terms of Service.
2. **No Fake Registration or Login**: Replays requiring registration forms, user accounts, or passwords are automatically skipped and logged as `registration form required`.
3. **Domain Rate Limiting**: All outbound HTTP and stream connections enforce a minimum `2.5s` delay between requests to the same domain.
4. **Header Identification**: User-Agent headers explicitly identify the research bot and contact email configured in `.env`.
5. **Authenticity Guarantee**: Output audio SHA256 checksums are verified to ensure zero overlap with legacy test synthetic datasets.

---

## 4. Mode 1 Browser Network Inspection & Media Streams Located

Under Mode 1 (Direct Media URL via browser network inspection), Playwright runs headless Chromium with `--disable-http2` and attaches network response listeners to intercept media manifests (`.m3u8`), audio segments, and progressive media files (`.mp3`, `.mp4`, `.m4a`).

### Verified Media Stream Routes:
- **Shopify (`SHOP`)**: `https://stream.mux.com/2EqBx4eDq1Ji4vU6p9Yi6JuhqueS1V3L00LjvrCRyshY.m3u8?redundant_streams=true` (Discovered via network interception on IR webcast player, duration: 58.1m).
- **Limbach Holdings (`LMB`)**: `https://event.choruscall.com/mediaframe/webcast.html?webcastid=LYkmLAUY` (Chorus Call player).
- **Enbridge (`ENB`)**: `https://events.q4inc.com/attendee/193728984` (Q4 Inc webcast container).
- **Canadian National Railway (`CNR`)**: `https://event.webcasts.com/starthere.jsp?ei=1774946&tp_key=06654de884&tp_special=8` (Notified / Webcasts.com).
- **Saputo (`SAP`)**: `https://www.gowebcasting.com/13127` (GoWebcasting media stream).

---

## 5. Optional Pre-Configured Replay Sources (`config/replay_sources.csv`)

The capture pipeline natively supports reading `config/replay_sources.csv` if manual/semi-automated browser inspection yields verified endpoints. The CSV conforms to the following schema:

```csv
ticker,replay_page_url,media_url,registration_required
SHOP,https://investors.shopify.com/events,https://stream.mux.com/2EqBx4eDq1Ji4vU6p9Yi6JuhqueS1V3L00LjvrCRyshY.m3u8?redundant_streams=true,False
```

When present, direct media URLs in `replay_sources.csv` are ingested with full validation gates (sample rate, mono, 16-bit PCM, >= 1200s duration, SHA256 novelty).

---

## 6. How to Reproduce Audio Capture

To execute the audio capture pipeline:

```bash
# 1. Ensure Phase 1 database schema is initialized and populated
python -m src.discovery.pipeline

# 2. Run Phase 2 Audio Capture Pipeline (Target: 7 new valid calls)
python -m src.capture.pipeline --limit 7
```

The pipeline outputs:
- Standardized audio files: `data/audio/<TICKER>_<fiscal_period>.wav`
- Audit manifest: `data/audio/capture_manifest.csv`
- Failures log: `data/audio/capture_failures.log`
- Rejected candidate files: `data/audio/rejected/<TICKER>_<fiscal_period>.wav`

