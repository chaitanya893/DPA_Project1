# Phase 2 Audio Capture Report & Failure Analysis

*Generated directly from `data/audio/capture_manifest.csv`, `data/audio/capture_failures.log`, and the Phase 1 `event_registry` database.*  
*Target Standard: 16 kHz, Mono, 16-bit PCM WAV, Duration $\ge 20$ minutes (1,200 s), Unique SHA-256.*

---

## 1. Automatic Sniffer Results (Playwright Network Interception)

The automated capture pipeline utilized headless Playwright (`chromium` with `--disable-http2` and network response interception listeners) to navigate directly to investor relations event portals and official vendor webcast players, following quarter-specific call links up to 2 hops.

- **Total Companies in Universe**: 25
- **Total Companies Attempted**: 25
- **Successfully Captured & Validated**: 1 (`SHOP` – Shopify Inc.)
  - **Source Endpoint**: `https://stream.mux.com/2EqBx4eDq1Ji4vU6p9Yi6JuhqueS1V3L00LjvrCRyshY.m3u8?redundant_streams=true`
  - **Standardized WAV**: `data/audio/SHOP_Q2_FY2026.wav`
  - **Duration**: 3,483.41 seconds (**58.1 minutes**)
  - **Audio Format**: 16,000 Hz, 1 Channel (Mono), 16-bit PCM
  - **File Size**: 111,469,304 bytes
  - **SHA-256**: `c8d344b684f4557e616b50d7b44f3cbe316b23141889e5c534005d33ef69d3a1`
  - **Status**: `VALID`
- **Total Uncaptured via Auto-Sniffer**: 24

---

## 2. Per-Company Execution & Failure Classification (25 Universe Companies)

The table below documents every company evaluated, detailing the exact failure categories and both attempts where URL re-routing was performed:

| Ticker | Company Name | Starting URL / Webcast Domain | Sniffer Result | Exact Failure Category & Detailed Log Reason |
| :--- | :--- | :--- | :--- | :--- |
| **SHOP** | Shopify Inc. | `stream.mux.com` | **CAPTURED** | **Valid full call captured via MUX HLS stream (58.1m)** |
| **AAPL** | Apple Inc. | `investor.apple.com` | Uncaptured | **no media URL found**: Player embedded in client JS; media loads only after user interaction. |
| **MSFT** | Microsoft Corporation | `microsoft.com` / `on24.com` | Uncaptured | **no media URL found**: ON24 console container requires interactive session init before stream handshake. |
| **JPM** | JPMorgan Chase & Co. | `jpmorganchase.com` | Uncaptured | **no media URL found**: Dynamic webcast player loads media asynchronously post-interaction. |
| **JNJ** | Johnson & Johnson | `investor.jnj.com` | Uncaptured | **no media URL found**: Player within nested script containers; audio stream URL not exposed in static DOM. |
| **XOM** | Exxon Mobil Corporation | `investor.exxonmobil.com` | Uncaptured | **no media URL found**: No media stream found on events portal (call time unannounced in results filing). |
| **TSLA** | Tesla Inc. | `ir.tesla.com` | Uncaptured | **no media URL found**: Proprietary player bundle encapsulates streaming endpoint. |
| **RELL** | Richardson Electronics | `rell.com` | Uncaptured | **no media URL found**: Media container loads stream asynchronously only after user engagement. |
| **ENB** | Enbridge Inc. | `events.q4inc.com` | Uncaptured | **no media URL found**: Q4 Inc attendee console requires interactive session bootstrap. |
| **ATD** | Alimentation Couche-Tard | `corpo.couche-tard.com` | Uncaptured | **no media URL found**: Media container loads stream only after manual interaction. |
| **MRU** | Metro Inc. | `corpo.metro.ca` | Uncaptured | **no media URL found**: Audio player embedded in dynamic event container. |
| **SAP** | Saputo Inc. | `gowebcasting.com` | Uncaptured | **no media URL found**: GoWebcasting player scripts obfuscate direct stream transport. |
| **WMT** | Walmart Inc. | `stock.walmart.com` | Uncaptured | **no media URL found**: IR event archive player initializes stream after client handshake. |
| **NTR** | Nutrien Ltd. | `nutrien.com` | Uncaptured | **no media URL found**: Dynamic player loads media stream after client-side trigger. |
| **T** | TELUS Corporation | `telus.com` | Uncaptured | **no media URL found**: Player scripts load audio assets only upon active playback controls. |
| **PESI** | Perma-Fix Environmental | `ir.perma-fix.com` | Uncaptured | **no media URL found**: Stream embedded within proprietary widget. |
| **APT** | Alpha Pro Tech | `alphaprotech.investorroom.com` | Uncaptured | **no media URL found**: Dynamic player container does not emit progressive stream without session. |
| **RY** | Royal Bank of Canada | `rbc.com` | Uncaptured | **no media URL found**: Player inside dynamic JavaScript components. |
| **PG** | Procter & Gamble | `pginvestor.com` | Uncaptured | **registration form required**: Mandatory user sign-up form encountered before access. |
| **ABX** | Barrick Gold | `barrick.com` | Uncaptured | **registration form required**: Webcast landing requires attendee registration form submission. |
| **GOOGL**| Alphabet Inc. | `abc.xyz` | Uncaptured | **registration form required**: Webcast viewer requires attendee registration form. |
| **LMB** | Limbach Holdings | `investors.limbachinc.com` &rarr;<br>`event.choruscall.com` | Uncaptured | **Attempt 1: DNS error** (`investors.limbachinc.com` &rarr; `ERR_NAME_NOT_RESOLVED`).<br>**Attempt 2: no media URL found** (`event.choruscall.com` requires active player frame runtime). |
| **DMRC** | Digimarc Corporation | `investors.digimarc.com` &rarr;<br>`digimarc.com/company/investors` | Uncaptured | **Attempt 1: DNS error** (`investors.digimarc.com` &rarr; `ERR_NAME_NOT_RESOLVED`).<br>**Attempt 2: no media URL found** (`digimarc.com/company/investors` has no static progressive stream). |
| **LLY** | Eli Lilly and Company | `investor.lilly.com` | Uncaptured | **HTTP2 protocol error**: Server returned `net::ERR_HTTP2_PROTOCOL_ERROR` / connection timeout. |
| **CNR** | Canadian National Railway | `event.webcasts.com` | Uncaptured | **page timeout**: Vendor player gateway timed out during page navigation and media collection. |

*(Note: No sources returned HTTP 403 or 429 rate-limiting blocks during media sniffing attempts).*

---

## 3. Aggregate Counts & Webcast Vendor Analysis (Total = 25)

### A. Categorical Breakdown (Total = 25 Unique Companies)
| Status / Failure Category | Company Count | Companies |
| :--- | :---: | :--- |
| **Successfully Captured (Auto-Sniffer)** | **1** | `SHOP` |
| **no media URL found** (Player inside iframe/JS, loads only post-interaction) | **17** | `AAPL`, `MSFT`, `JPM`, `JNJ`, `XOM`, `TSLA`, `RELL`, `ENB`, `ATD`, `MRU`, `SAP`, `WMT`, `NTR`, `T`, `PESI`, `APT`, `RY` |
| **registration form required** | **3** | `PG`, `ABX`, `GOOGL` |
| **DNS error &rarr; no media URL found** (Two attempts: DNS failure then JS player) | **2** | `LMB`, `DMRC` |
| **HTTP2 protocol error** | **1** | `LLY` |
| **page timeout** | **1** | `CNR` |
| **blocked** (HTTP 403 / 429) | **0** | *None* |
| **Total Universe Companies** | **25** | |

### B. Webcast Platform Vendor Distribution (`event_registry.vendor`)
| Vendor Name | Total in Registry | Auto-Captured | Primary Failure Mode |
| :--- | :---: | :---: | :--- |
| **In-house / Custom IR** | 21 | 1 (`SHOP`) | Media stream encapsulated behind dynamic client-side player scripts |
| **ON24** | 1 | 0 | Interactive session initialization required (`MSFT`) |
| **Chorus Call** | 1 | 0 | Stream handshake requires active mediaframe runtime (`LMB`) |
| **Q4 Inc** | 1 | 0 | Attendee viewer encapsulates audio payload (`ENB`) |
| **Notified / Webcasts.com** | 1 | 0 | Complex JS console and gateway timeout (`SAP`, `CNR`) |
| **Total** | **25** | **1** | |

---

## 4. PDF Phase 2 Mode 1 – Media URL from the Browser Network Tab

In accordance with Phase 2, Mode 1 of the project specification, where vendor players encapsulate media streams behind client-side JavaScript execution, session handshakes, or iframes, direct media endpoints (`.m3u8` master manifests, `.mp3` progressive streams, or `.mp4` audio tracks) are obtained via the browser developer tools network panel and cataloged in `config/replay_sources.csv`.

Once direct media URLs are entered into `config/replay_sources.csv`, the remainder of the pipeline remains **100% automated**:
1. Automated ingestion via `ffmpeg` / `yt-dlp` with domain rate-limiting and user-agent identification.
2. Conversion and standardization to 16 kHz, Mono, 16-bit PCM WAV.
3. Automated validation gates (duration $\ge 1,200\text{ s}$, sample rate, mono channel, bit depth, SHA-256 novelty).
4. Manifest updating in `data/audio/capture_manifest.csv` with `url_located_by = network_tab`.

### Verified Network Tab Replay Sources (`config/replay_sources.csv`):

| Ticker | Replay Page URL | Media URL (from Network Tab) | Registration Required | Notes |
| :--- | :--- | :--- | :---: | :--- |
| *(Pending)* | - | - | - | Table to be populated from browser inspection. |

---

## 5. Audit Trail & Manifest Provenance

The audit manifest [`data/audio/capture_manifest.csv`](file:///c:/Users/chait/Desktop/DPA_Project1/data/audio/capture_manifest.csv) records each event with the `url_located_by` provenance column:
- `SHOP`: `url_located_by = auto_sniffer`
- Remaining 24 uncaptured events: `url_located_by = auto_sniffer`
- Any future entries ingested via manual network tab identification will be recorded as `url_located_by = network_tab`.
