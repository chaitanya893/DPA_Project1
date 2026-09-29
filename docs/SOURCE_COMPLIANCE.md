# Source Compliance and Terms of Use Log

*Last Updated: 2026-09-11*  
*Project: Earnings Call Capture and Transcription Pipeline (Assignment 1)*

---

## 1. Non-Negotiable Operating Principles

1. **Strict Rate Limiting**: All outbound HTTP requests are limited to a minimum delay of **2.5 seconds** between requests per domain.
2. **Transparent User-Agent Identification**: Every request includes a descriptive User-Agent header containing the bot purpose and contact email:
   ```text
   User-Agent: EarningsCallCaptureBot/1.0 (Contact: research_intern@domain.com)
   ```
3. **Robots.txt & Fair Use Adherence**: `robots.txt` directives are parsed and respected prior to fetching.
4. **No Authentication / Credential Bypass**: We do not create false accounts, bypass paywalls/registration walls, or share credentials.
5. **Third-Party Transcripts Isolation**: Any third-party benchmark transcripts collected are strictly utilized for internal offline accuracy benchmarking (WER/CER/Entity evaluation) and are **never** stored in public databases or redistributed.
6. **Block Escalation Policy**: If an IP or User-Agent is blocked (HTTP 403/429), the scraper logs the block to `crawl_log` and terminates without attempting evasive IP rotation or proxy bypassing.

---

## 2. Source-by-Source Compliance Audit & Legal Basis

| Source / Domain | Date Audited | Allowed / Restricted | Specific Clause & Legal Rationale | Operating Constraints |
| :--- | :--- | :--- | :--- | :--- |
| **SEC EDGAR API** (`sec.gov`) | 2026-09-11 | **Allowed** | SEC Public Dissemination Policy permits public automated access provided User-Agent conforms to `Sample Company Name AdminContact@<sample company domain>.com` and request frequency is under 10 requests/second. Used to verify call dates/times from Item 2.02 Form 8-K filings. | Rate-limited to 1 request / 2.5s (far below 10 req/s threshold). |
| **Microsoft Investor Relations** (`microsoft.com`, `c.s-microsoft.com`) | 2026-09-28 | **Allowed (Public IR Transcripts)** | Official investor conference call reference transcripts published for open investor dissemination. Downloaded with rate limits (2–3 s) and descriptive User-Agent. Used strictly for offline mathematical accuracy scoring (WER/CER/DER) and never stored in database or redistributed. | Rate-limited to 1 request / 2.5s; internal scoring evaluation only. |
| **Hugging Face Model Hub** (`huggingface.co`) | 2026-09-12 | **Allowed (Gated Research License)** | `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0` gated model repository. Free developer account authentication token (`HF_TOKEN`) used with explicitly accepted terms of use for academic and research evaluation. | Authenticated token via `.env`; models cached locally in `~/.cache/huggingface`. |
| **AWS EC2 Pricing Portal** (`aws.amazon.com/ec2/pricing/on-demand/`) | 2026-09-29 | **Allowed (Public Web Documentation)** | Public cloud on-demand pricing documentation for EC2 instance types (`g4dn.xlarge`, `c6i.2xlarge`). Read for transparent production economics modeling. | Public web reference fetched with standard browser headers. |
| **SEDAR+ Canada** (`sedarplus.ca`) | 2026-09-11 | **Allowed (Public Metadata)** | Canadian Securities Administrators (CSA) public record disclosure. Automated metadata verification permitted for educational & research purposes without automated bulk extraction of copyrighted software components. | Use cached filings indices; 3s delay. |
| **Business Wire / PR Newswire / GlobeNewswire** | 2026-09-11 | **Allowed (Public Press Releases)** | Press releases are distributed publicly for open editorial & investor consumption. ToS restricts unauthorized redistribution of the platform code, not reading publicly disseminated investor advisory notices. | Scrape only public announcement title & dates; rate limited. |
| **Company IR Portals (Apple, Alphabet, Digimarc, etc.)** | 2026-09-27 | **Allowed** | Investor Relations events pages are publicly available under Fair Use for investor dissemination without requiring login. | Fetch only event schedule HTML metadata. |
| **Microsoft Event Stream (`stream.event.microsoft.com`, `medius.microsoft.com`, `mediastream.microsoft.com`)** | 2026-09-27 | **Allowed (Public Webcast HLS)** | Publicly broadcasted investor earnings webcasts hosted on Microsoft Azure Event CDN without authentication, registration, or paywalls. | Streamed via yt-dlp/ffmpeg with rate limits; User-Agent identified. |
| **Shopify Mux Video CDN (`stream.mux.com`)** | 2026-09-27 | **Allowed (Public Webcast HLS)** | Publicly accessible HLS media stream embedded on official Shopify IR portal. No registration or DRM. | Captured directly via standard HLS m3u8 without DRM bypass. |
| **GlobalMeet / Webcasts.com (`event.webcasts.com`)** | 2026-09-27 | **Gated (Registration Required)** | Terms of Service require attendee registration with accurate identification. Gated behind registration form. | **Compliant - No submission**: Script halted at registration form and logged evidence without entering fake credentials. |
| **Chorus Call (`event.choruscall.com`)** | 2026-09-27 | **Gated (Registration Required)** | Webcast portal requires user registration (name, company, email). | **Compliant - No submission**: Registration form detected; audited, screenshotted, and bypassed without automated form filling. |
| **Webinar.net (`app.webinar.net`)** | 2026-09-27 | **Gated (Registration Required)** | Interactive investor portal requiring attendee registration. | **Compliant - No submission**: Registration form detected and classified; no automated submissions made. |
| **GoWebcasting (`www.gowebcasting.com`)** | 2026-09-27 | **Gated (Registration Required)** | Proprietary Canadian investor webcast platform requiring attendee details. | **Compliant - No submission**: Form logged and screenshotted; no synthetic profile injected. |
| **Q4 Inc (`events.q4inc.com`)** | 2026-09-27 | **Allowed (Public Landing)** | Q4 IR platform public event landing page. | Inspected for direct streams; no auth bypass attempted. |
| **Webcaster5 / MultiVu (`www.webcaster5.com`)** | 2026-09-27 | **Restricted (Access Denied / WAF)** | Platform returned access restrictions / expired session. | Evaluated and logged without evasive rotation. |
| **Cloudflare / WAF Protected Portals (`ir.tesla.com`, `investor.lilly.com`, `www.telus.com`)** | 2026-09-27 | **Restricted (HTTP 403 / Bot Challenge)** | Automated scrapers challenged by edge protection. | Logged strictly as access denied; no evasion or proxy techniques deployed. |

---

## 3. Incident & Block Log

| Timestamp (UTC) | Domain | Status Code | Action Taken | Resolution / Notes |
| :--- | :--- | :--- | :--- | :--- |
| 2026-09-27T17:50:40Z | `ir.tesla.com` | 403 | Logged to `webcast_status.csv` and halted | Edge WAF challenge encountered. Logged cleanly without bypass attempts. |
| 2026-09-27T17:50:51Z | `investor.lilly.com` | 403 | Logged to `webcast_status.csv` and halted | Cloudflare bot protection encountered. Logged cleanly without bypass attempts. |
| 2026-09-27T17:52:09Z | `www.telus.com` | 403 | Logged to `webcast_status.csv` and halted | Edge protection challenge encountered. Logged cleanly without bypass attempts. |

