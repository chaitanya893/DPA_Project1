# Phase 2 Audio Capture Report & Webcast Platform Analysis

*Generated directly from `data/audio/capture_manifest.csv`, `data/audio/webcast_status.csv`, and `data/audio/capture_failures.log`.*  
*Target Standard: 16 kHz, Mono, 16-bit PCM WAV, Duration $\ge 20$ minutes (1,200 s) and $\le 3$ hours (10,800 s), Unique SHA-256.*

---

## 1. Valid Captured Earnings Calls Summary (12 Calls)

A total of **12 full earnings calls** were successfully captured, standardized to 16 kHz mono 16-bit PCM WAV, validated against all quality and integrity gates, and registered in `data/audio/capture_manifest.csv`.

| Ticker | Fiscal Period | Duration | Audio Path | Source Domain | Vendor Parser |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **SHOP** | Q2 FY2026 | 58.1m | `data/audio/SHOP_Q2_FY2026.wav` | `stream.mux.com` | Shopify Mux Player Parser |
| **SHOP** | Q1 FY2026 | 63.0m | `data/audio/SHOP_Q1_FY2026.wav` | `stream.mux.com` | Shopify Mux Player Parser |
| **MSFT** | Q4 FY2026 | 64.5m | `data/audio/MSFT_Q4_FY2026.wav` | `stream.event.microsoft.com` | Microsoft Medius Player Parser |
| **MSFT** | Q3 FY2026 | 62.4m | `data/audio/MSFT_Q3_FY2026.wav` | `stream.event.microsoft.com` | Microsoft Medius Player Parser |
| **MSFT** | Q2 FY2026 | 57.7m | `data/audio/MSFT_Q2_FY2026.wav` | `stream.event.microsoft.com` | Microsoft Medius Player Parser |
| **MSFT** | Q1 FY2026 | 58.6m | `data/audio/MSFT_Q1_FY2026.wav` | `stream.event.microsoft.com` | Microsoft Medius Player Parser |
| **MSFT** | Q4 FY2025 | 55.1m | `data/audio/MSFT_Q4_FY2025.wav` | `stream.event.microsoft.com` | Microsoft Medius Player Parser |
| **MSFT** | Q3 FY2025 | 56.5m | `data/audio/MSFT_Q3_FY2025.wav` | `stream.event.microsoft.com` | Microsoft Mediastream JSON Parser |
| **MSFT** | Q2 FY2025 | 58.2m | `data/audio/MSFT_Q2_FY2025.wav` | `stream.event.microsoft.com` | Microsoft Mediastream JSON Parser |
| **MSFT** | Q1 FY2025 | 63.0m | `data/audio/MSFT_Q1_FY2025.wav` | `stream.event.microsoft.com` | Microsoft Medius Player Parser |
| **MSFT** | Q3 FY2024 | 60.2m | `data/audio/MSFT_Q3_FY2024.wav` | `stream.event.microsoft.com` | Microsoft Medius Player Parser |
| **MSFT** | Q2 FY2024 | 61.3m | `data/audio/MSFT_Q2_FY2024.wav` | `stream.event.microsoft.com` | Microsoft Medius Player Parser |

---

## 2. Automated Webcast Status & Evidence for all 25 Universe Companies

Each company's latest quarterly earnings webcast URL was opened in headless Playwright (Chromium, `--disable-http2`, 15 s DOM load, wait until no "Loading" text) without submitting forms. Results were classified from live DOM contents, and visual evidence was saved to `docs/evidence/`.

| # | Ticker | Webcast / Event URL | URL Source | Status | HTTP | Evidence Screenshot |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- |
| 1 | **AAPL** | `https://www.apple.com/investor/earnings-call/` | `press_release` | no webcast link found | 200 | [AAPL Screenshot](evidence/AAPL_no_webcast_link_found.png) |
| 2 | **MSFT** | `https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4` | `ir_page_link` | **media found** | 200 | [MSFT Screenshot](evidence/MSFT_media_found.png) |
| 3 | **JPM** | `https://event.webcasts.com/starthere.jsp?ei=1767182&tp_key=dd05e5b127&tp_special=8` | `press_release` | **registration form** | 200 | [JPM Screenshot](evidence/JPM_registration_form.png) |
| 4 | **JNJ** | `https://investor.jnj.com` | `ir_page_link` | **blocked – bot protection (HTTP 403)** | 403 | [JNJ Screenshot](evidence/JNJ_blocked_bot_protection_HTTP_403.png) |
| 5 | **XOM** | `https://event.webcasts.com/starthere.jsp?ei=1770134&tp_key=90907396e5` | `ir_page_link` | **registration form** | 200 | [XOM Screenshot](evidence/XOM_registration_form.png) |
| 6 | **WMT** | `https://corporate.walmart.com/news/2026/08/13/walmart-to-host-second-quarter-earnings-conference-call-august-20-2026` | `ir_page_link` | no webcast link found | 200 | [WMT Screenshot](evidence/WMT_no_webcast_link_found.png) |
| 7 | **GOOGL** | `https://www.youtube.com/watch?v=LzExSq9DU9w` | `press_release` | **media only on YouTube – not usable (YouTube ToS forbids downloading)** | 200 | [GOOGL Screenshot](evidence/GOOGL_media_only_on_YouTube.png) |
| 8 | **TSLA** | `https://ir.tesla.com` | `press_release` | **blocked – bot protection (HTTP 403)** | 403 | [TSLA Screenshot](evidence/TSLA_blocked_bot_protection_HTTP_403.png) |
| 9 | **PG** | `https://www.pginvestor.com/news/news-details/2026/PG-to-Webcast-Discussion-of-First-Quarter-2627-Earnings-Results-on-October-22/default.aspx` | `ir_page_link` | **registration form** | 200 | [PG Screenshot](evidence/PG_registration_form.png) |
| 10 | **LLY** | `https://investor.lilly.com/webcasts-and-presentations` | `press_release` | **blocked – bot protection (HTTP 403)** | 403 | [LLY Screenshot](evidence/LLY_blocked_bot_protection_HTTP_403.png) |
| 11 | **LMB** | `https://event.choruscall.com/mediaframe/webcast.html?webcastid=LYkmLAUY` | `press_release` | **registration form** | 200 | [LMB Screenshot](evidence/LMB_registration_form.png) |
| 12 | **APT** | `https://www.alphaprotech.com/investors` | `ir_page_link` | no webcast link found | 200 | [APT Screenshot](evidence/APT_no_webcast_link_found.png) |
| 13 | **DMRC** | `https://edge.media-server.com/mmc/p/mmdzxsei/` | `press_release` | **registration form** | 200 | [DMRC Screenshot](evidence/DMRC_registration_form.png) |
| 14 | **RELL** | `https://www.rell.com/press-room/events` | `ir_page_link` | no webcast link found | 200 | [RELL Screenshot](evidence/RELL_no_webcast_link_found.png) |
| 15 | **PESI** | `https://www.webcaster5.com/Webcast/Page/2243/54338` | `press_release` | **registration form** | 200 | [PESI Screenshot](evidence/PESI_registration_form.png) |
| 16 | **RY** | `https://www.rbc.com/investorrelations/quarterly-financial-statements.html` | `press_release` | **404** | 404 | [RY Screenshot](evidence/RY_404.png) |
| 17 | **ENB** | `https://events.q4inc.com/attendee/193728984` | `press_release` | **registration form** | 200 | [ENB Screenshot](evidence/ENB_registration_form.png) |
| 18 | **CNR** | `https://event.webcasts.com/starthere.jsp?ei=1774946&tp_key=06654de884&tp_special=8` | `press_release` | **registration form** | 200 | [CNR Screenshot](evidence/CNR_registration_form.png) |
| 19 | **SHOP** | `https://www.shopify.com/investors/quarterly-results/webcast/q2-2026` | `ir_page_link` | **media found** | 200 | [SHOP Screenshot](evidence/SHOP_media_found.png) |
| 20 | **ABX** | `https://www.barrick.com/English/investors/default.aspx` | `ir_page_link` | **blocked – bot protection (HTTP 403)** | 403 | [ABX Screenshot](evidence/ABX_blocked_bot_protection_HTTP_403.png) |
| 21 | **T** | `https://www.telus.com/en/about/investor-relations` | `ir_page_link` | **blocked – bot protection (HTTP 403)** | 403 | [T Screenshot](evidence/T_blocked_bot_protection_HTTP_403.png) |
| 22 | **NTR** | `https://www.nutrien.com/news/events/2026-q2-earnings-conference-call` | `ir_page_link` | no webcast link found | 200 | [NTR Screenshot](evidence/NTR_no_webcast_link_found.png) |
| 23 | **ATD** | `https://app.webinar.net/6YK41Lp1oz2` | `press_release` | **registration form** | 200 | [ATD Screenshot](evidence/ATD_registration_form.png) |
| 24 | **MRU** | `https://corpo.metro.ca/en/investor-relations.html` | `ir_page_link` | no webcast link found | 200 | [MRU Screenshot](evidence/MRU_no_webcast_link_found.png) |
| 25 | **SAP** | `https://www.gowebcasting.com/13127` | `press_release` | **registration form** | 200 | [SAP Screenshot](evidence/SAP_registration_form.png) |

---

## 3. Aggregate Webcast Status & Vendor Distribution

### A. Counts by Status Category (Total = 25)
| Status Category | Count | Companies | Description |
| :--- | :---: | :--- | :--- |
| **registration form** | **10** | `JPM`, `XOM`, `PG`, `LMB`, `DMRC`, `PESI`, `ENB`, `CNR`, `ATD`, `SAP` | Attendee sign-up form required (skipped per compliance rules) |
| **no webcast link found** | **6** | `AAPL`, `WMT`, `APT`, `RELL`, `NTR`, `MRU` | IR landing page or news release contains document links/transcripts only, no active webcast audio player |
| **blocked – bot protection (HTTP 403)** | **5** | `JNJ`, `TSLA`, `LLY`, `ABX`, `T` | WAF / Cloudflare bot protection on IR portal (HTTP 403) |
| **media found** | **2** | `MSFT`, `SHOP` | Direct HLS media streams accessible without gating |
| **media only on YouTube – not usable** | **1** | `GOOGL` | Audio broadcast on YouTube (YouTube ToS forbids downloading; compliant skip) |
| **404** | **1** | `RY` | Press release webcast URL returns HTTP 404 |
| **Total** | **25** | | |

### B. Counts by Vendor Platform Domain
| Vendor Platform / Domain | Total | Media Accessible | Gating / Failure Modes |
| :--- | :---: | :---: | :--- |
| **Company In-House IR / CDN** (`microsoft.com`, `shopify.com`, `apple.com`, `stock.walmart.com`, `alphaprotech.com`, `rell.com`, `corpo.metro.ca`, `nutrien.com`) | 8 | 2 (`MSFT`, `SHOP`) | No Direct Webcast Link (6) |
| **WAF / Cloudflare Protected IR** (`ir.tesla.com`, `investor.jnj.com`, `investor.lilly.com`, `barrick.com`, `telus.com`) | 5 | 0 | Edge Bot Protection HTTP 403 (5) |
| **GlobalMeet / Webcasts.com** (`event.webcasts.com`) | 3 | 0 | Registration forms (`JPM`, `XOM`, `CNR`) |
| **Q4 Inc** (`events.q4inc.com`, `pginvestor.com`) | 2 | 0 | Registration forms (`ENB`, `PG`) |
| **Chorus Call** (`event.choruscall.com`) | 1 | 0 | Registration form (`LMB`) |
| **Webinar.net** (`app.webinar.net`) | 1 | 0 | Registration form (`ATD`) |
| **GoWebcasting** (`gowebcasting.com`) | 1 | 0 | Registration form (`SAP`) |
| **Media-Server / Notified** (`edge.media-server.com`) | 1 | 0 | Registration form (`DMRC`) |
| **Multivu / Webcaster5** (`webcaster5.com`) | 1 | 0 | Registration form (`PESI`) |
| **YouTube** (`youtube.com`) | 1 | 0 | YouTube ToS Download Restriction (`GOOGL`) |
| **Royal Bank of Canada** (`rbc.com`) | 1 | 0 | HTTP 404 on Press Release URL (`RY`) |
| **Total** | **25** | **2** | |


---

## 4. Key Findings & Pipeline Limitations

### Key Finding: Public vs. Gated Webcasts
- **Company-Hosted Custom Players Are Ungated**: Only Microsoft (Medius and Mediastream platforms hosted on `stream.event.microsoft.com`) and Shopify (Mux Video CDN on `stream.mux.com`) provide fully ungated public HLS streams (`.m3u8`) without requiring attendee registration, logins, or interactive session handshakes.
- **Third-Party Webcast Vendors Require Registration**: All major third-party investor relations platforms (GlobalMeet / Webcasts.com, Chorus Call, Webinar.net, GoWebcasting) enforce attendee registration forms collecting user email and company details. In strict compliance with project ethics and terms of service, these forms were **never filled**.

### Dataset Limitations
- **Company Concentration**: All 12 valid audio calls originate from 2 enterprise software companies (`MSFT` and `SHOP`).
- **Distribution Metrics**: Because 10 calls are Microsoft and 2 are Shopify:
  - **Market Cap**: All 12 calls belong to the `large_cap` bucket (no small-cap representation in the captured audio set).
  - **Language**: All 12 calls are in English (the bilingual French/English Canadian calls from `ATD`, `MRU`, and `SAP` could not be captured due to registration walls and 404s).
- **Temporal Span**: The captured Microsoft calls span across 3 fiscal years (FY2026, FY2025, FY2024), providing comprehensive temporal continuity for acoustic and speech recognition benchmarking.
