# Corporate Earnings Call Pipeline – Event Discovery Memo

**Generated:** 2026-09-27 06:26:11 UTC  
**Evaluation Scope:** 25 Universe Companies (US Large Cap, US Small Cap, Canadian TSX, Canadian Bilingual)  
**Total Discovered Events:** 13/25 with verified date and time (12/25 unannounced / time omitted)  
**Total Real HTTP Requests Logged in DB:** 316  

---

## 1. Analysis of All Six PDF Discovery Routes

| Discovery Route / Channel | Utilized in Production | Operational Assessment & Reliability Findings |
| :--- | :---: | :--- |
| **1. SEC EDGAR (8-K Item 2.02 / 6-K Exhibits)** | **YES** | **Primary and most authoritative route for US & Interlisted Canadian issuers.** EX-99.1 press release exhibit provides definitive timestamps, timezone, dial-in, and participant details. |
| **2. SEDAR+ (Canada Filing System)** | **NO** | Lacks a public full-text programmatic REST API and enforces Cloudflare bot protection; interlisted Canadian issuers are resolved via SEC EDGAR 6-K filings. |
| **3. Company IR Events Pages & RSS Feeds** | **YES** | **Universal fallback route.** Scrapes event widgets, HTML tables, and webcast links for TSX-only companies (ATD, MRU, SAP) and issuers without EDGAR call advisories. |
| **4. Commercial Newswires (CNW / Business Wire)** | **NO** | Not implemented in automated pipeline; all verified calls are derived directly from primary regulatory filings (SEC EDGAR 8-K/6-K exhibits) and official issuer IR pages. |
| **5. Webcast Vendor Direct Platforms** | **YES** | Direct vendor URLs (Q4, Notified, ON24, Chorus Call) classified from exhibit/page links via 1-hop inspection. |
| **6. Public Financial Calendars (Yahoo/Investing)** | **NO (Excluded)** | Excluded due to ToS restrictions, rate-limit blocking, and unverified date estimates. |

---

## 2. Discovery Route Performance & Measured Lead Times

| Route | Entities Discovered | Share (%) |
| :--- | :---: | :---: |
| **SEC_EDGAR_8-K** | 17 | 68.0% |
| **SEC_EDGAR_6-K** | 5 | 20.0% |
| **IR_EVENTS_PAGE** | 3 | 12.0% |

### Median Announcement Lead Time by Route (Measured from Filing acceptanceDateTime to Call Datetime)
| Discovery Route | Measured Call Count | Median Lead Time (Announcement to Call) |
| :--- | :---: | :---: |
| **SEC_EDGAR_8-K** | 11 events | **1.5 hours (0.1 days)** |
| **SEC_EDGAR_6-K** | 1 events | **2.2 hours (0.1 days)** |

- **Earliest route**: SEC_EDGAR_6-K (2.2 hours / 0.1 days median lead time)
- **Primary Route**: SEC EDGAR Form 8-K / 6-K Press Release Exhibits.
- **Most Reliable Route**: SEC EDGAR submissions combined with direct company IR page scrapers.

---

## 3. Webcast Vendor Distribution across the Universe

| Webcast Platform / Vendor | Count | Distribution (%) |
| :--- | :---: | :---: |
| **In-house** | 22 | 88.0% |
| **ON24** | 1 | 4.0% |
| **Q4 Inc** | 1 | 4.0% |
| **Notified** | 1 | 4.0% |

---

## 4. Companies Missing Date/Time (Real Reason Logged)

- **XOM**: Call date/time omitted in filing press release
- **WMT**: Call date/time omitted in filing press release
- **PG**: Call date/time omitted in filing press release
- **APT**: Call date/time omitted in filing press release
- **DMRC**: Call date/time omitted in filing press release
- **PESI**: Call date/time omitted in filing press release
- **ABX**: Call date/time omitted in filing press release
- **T**: Call date/time omitted in filing press release
- **NTR**: Call date/time omitted in filing press release
- **ATD**: No upcoming call announced on official IR page
- **MRU**: No upcoming call announced on official IR page
- **SAP**: No upcoming call announced on official IR page

---

## 5. Crawl Logs & Compliance Summary

- **Total Requests Executed**: 316
- **HTTP 200 Successes**: 300
- **Rate Limit Adherence**: Enforced 2.5s per domain delay with compliant User-Agent
