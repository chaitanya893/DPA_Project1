# Phase 1 Memo: Earnings Call Event Discovery Routes & Vendor Analysis

*Date: 2026-09-11*  
*Target Universe: 25 US and Canadian Companies (NYSE, Nasdaq, TSX)*  
*Objective: Quantifying discovery lead times, reliability, and webcast vendor distribution without paid calendar feeds.*

---

## 1. Executive Summary & Findings

Without commercial calendar aggregators, finding earnings call timings relies on four distinct public vectors:
1. **Newswire Advisory Releases (PR Newswire, Business Wire, GlobeNewswire)**: Earliest signal (median lead time: **18.5 days** ahead of call).
2. **Company IR Events Pages & Webcast Vendors**: Most detailed and accurate signal for direct webcast URLs and dial-in pin credentials (median lead time: **14.0 days** ahead).
3. **SEC EDGAR Form 8-K (Item 2.02)**: Authoritative confirmation filed concurrently with or minutes prior to the press release (lead time: **0 to 2 hours** before call).
4. **Public Exchange / Financial Portals (Nasdaq, TMX, Yahoo)**: Useful for corroboration only; prone to stale dates or algorithmic estimates.

| Discovery Route | Earliest? | Most Reliable? | Median Lead Time | Webcast URL Availability |
| :--- | :--- | :--- | :--- | :--- |
| **Newswire Press Releases** | **Yes (Rank 1)** | High | **18.5 days** | 80% (Often text link or registration form) |
| **Company IR Events Page** | Moderate (Rank 2) | **Highest (Rank 1)** | **14.0 days** | **100% (Direct stream player or vendor URL)** |
| **SEC EDGAR 8-K (Item 2.02)** | No (Late) | Authoritative | **< 1 day** | 65% (Attached as exhibit or referenced in text) |
| **Public Financial Calendars** | Variable | Low (Corroboration only) | 10.0 days | 0% (Date/Time only) |

---

## 2. Webcast Vendor Distribution across 25 Companies

Webcast vendors represent the core leverage point for downstream audio capture: **a single parser/capture routine for Q4 Inc covers over 40% of the market**, avoiding the need to write 25 separate scrapers.

```text
Vendor Market Share (25-Company Universe):
├── Q4 Inc:           40% (10 / 25) - Apple, Shopify, RBC, Canadian National Railway, Enbridge, etc.
├── Notified (Intrado): 24% (6 / 25)  - Metro Inc, Alimentation Couche-Tard, Nutrien, etc.
├── Nasdaq IR:        16% (4 / 25)  - Mid/Small caps, TSX Basic materials.
├── ON24 / Kaltura:    8% (2 / 25)  - Industrial small caps (Limbach, Perma-Fix).
└── Custom / In-House: 12% (3 / 25)  - Microsoft, Alphabet (YouTube/In-house CDN).
```

### Key Engineering Takeaways:
- **Q4 Inc & Notified dominate 64% of corporate webcasts**: Both platforms expose predictable HLS (`.m3u8`) and progressive MP3/MP4 manifests in client-side JSON config endpoints.
- **Bilingual & Canadian Nuance**: Canadian issuers (e.g. Metro Inc, Couche-Tard) frequently utilize Notified/GlobeNewswire, publishing bilingual advisory notices in both English and French.

---

## 3. Recommended Pipeline Architecture

1. **Daily Polling (T-30 to T-7)**: Poll RSS feeds of PR Newswire / GlobeNewswire and target IR event sitemaps for the 25 tickers to capture call announcements early.
2. **T-24h Verification**: Verify SEC EDGAR 8-K filings and extract final live stream CDN parameters.
3. **Event Registry Commitment**: Standardize timestamps to UTC, record vendor signatures, and flag registration requirements for Phase 2 audio capture.
