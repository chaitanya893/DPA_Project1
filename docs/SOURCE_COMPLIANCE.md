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
| **SEC EDGAR API** (`sec.gov`) | 2026-09-11 | **Allowed** | SEC Public Dissemination Policy permits public automated access provided User-Agent conforms to `Sample Company Name AdminContact@<sample company domain>.com` and request frequency is under 10 requests/second. | Rate-limited to 1 request / 2.5s (far below 10 req/s threshold). |
| **SEDAR+ Canada** (`sedarplus.ca`) | 2026-09-11 | **Allowed (Public Metadata)** | Canadian Securities Administrators (CSA) public record disclosure. Automated metadata verification permitted for educational & research purposes without automated bulk extraction of copyrighted software components. | Use cached filings indices; 3s delay. |
| **Business Wire / PR Newswire / GlobeNewswire** | 2026-09-11 | **Allowed (Public Press Releases)** | Press releases are distributed publicly for open editorial & investor consumption. ToS restricts unauthorized redistribution of the platform code, not reading publicly disseminated investor advisory notices. | Scrape only public announcement title & dates; rate limited. |
| **Company IR Portals (Apple, Microsoft, RBC, etc.)** | 2026-09-11 | **Allowed** | Investor Relations events pages are publicly available under Fair Use for investor dissemination without requiring login. | Fetch only event schedule HTML metadata. |
| **Webcast CDNs (Q4 Inc, Notified, Nasdaq IR, Zoom)** | 2026-09-11 | **Allowed (Public Streams)** | Public webcasts without DRM or required registration fees. Streams are recorded for academic evaluation and transcript generation. | Captured directly via standard progressive media or HLS URLs without bypassing DRM. |

---

## 3. Incident & Block Log

| Timestamp (UTC) | Domain | Status Code | Action Taken | Resolution / Notes |
| :--- | :--- | :--- | :--- | :--- |
| *None* | - | - | - | System initialised without incidents. |
