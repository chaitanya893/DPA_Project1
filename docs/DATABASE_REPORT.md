# Database Audit & Architecture Report

*Project: Financial Earnings Audio Transcription & Diarization Pipeline*  
*Audit Timestamp: 2026-09-29*

---

## 1. Executive Summary & Database Architecture

The pipeline uses a relational database schema managed via **SQLAlchemy ORM** to track company metadata, discovered earnings events, and crawler audit logs.

### Database Engine & Configuration
* **Default Local Engine**: **SQLite** (`earnings_call.db` in repository root, 112 KB).
* **Production PostgreSQL Engine**: Configured seamlessly by providing `DATABASE_URL=postgresql://user:password@host:port/dbname` in `.env`.
* **Housekeeping Note**: An empty 0-byte file `data/earnings_calls.db` was identified as an unused legacy artifact; it was verified to have no code dependencies and was safely removed.

### Division of Responsibility: Database vs. File Storage
To maintain high performance and legal compliance, data responsibilities are strictly separated:
1. **Stored in Database (`earnings_call.db`)**:
   * `company_universe` (25 rows): Target public company metadata (ticker, name, exchange, country, CIK/SEDAR ID, market cap bucket, language).
   * `event_registry` (36 rows): Discovered earnings events, SEC filing dates, call datetimes (UTC), webcast URLs, vendor classification, registration requirements, and confidence scores.
   * `crawl_log` (540 rows): Structured audit trail for all discovery and capture web requests (timestamp, target URL, HTTP status code, outcome, duration, error message, correlation ID).
2. **Stored in File Storage (`data/transcripts/`, `data/audio/`, `docs/`)**:
   * **JSON Transcripts** (`data/transcripts/*.json`): 12 complete structured deliverable transcripts adhering to the required schema.
   * **Execution Metrics** (`data/transcripts/metrics/*_metrics.json`): Per-call latency, ASR inference time, diarization duration, and SLA status.
   * **WAV Audio Files** (`data/audio/*.wav`): Standardized 16 kHz Mono 16-bit PCM audio files (gitignored, tracked via `capture_manifest.csv`).
3. **Legal Compliance Isolation (Reference Transcripts)**:
   * Third-party official reference transcripts downloaded for mathematical scoring (`data/reference/transcripts/`) are **strictly excluded from the database** and repository redistribution per project compliance rules (see [`docs/SOURCE_COMPLIANCE.md`](SOURCE_COMPLIANCE.md)).

---

## 2. Live Database Inspection Output (`scripts/db_report.py`)

Executing `python scripts/db_report.py` against `earnings_call.db` produces the following verified state:

```text
=========================================================================================================
  EARNINGS CALL DATABASE AUDIT REPORT
  Database Engine: sqlite (earnings_call.db)
=========================================================================================================

--- 1. TABLE NAMES & ROW COUNTS ---
  * company_universe       :   25 rows
  * crawl_log              :  540 rows
  * event_registry         :   36 rows

--- 2. EVENT REGISTRY (25 UNIVERSE COMPANIES) ---
#   | Ticker | Fiscal Period | Call Datetime (UTC)      | Vendor       | Reg Required | Discovery Source   | Confidence
-------------------------------------------------------------------------------------------------------------------
1   | AAPL   | Q3 FY2026     | 2026-07-30 21:00:00Z     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.95      
2   | MSFT   | Q4 FY2026     | 2026-07-29 21:30:00Z     | Medius       | Unknown      | SEC_EDGAR_8-K      | 0.95      
3   | JPM    | Q2 FY2026     | 2026-07-14 12:30:00Z     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.95      
4   | JNJ    | Q2 FY2026     | 2026-07-15 12:30:00Z     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.95      
5   | XOM    | Q2 FY2026     | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.60      
6   | WMT    | Q2 FY2027     | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.60      
7   | GOOGL  | Q2 FY2026     | 2026-07-22 20:30:00Z     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.95      
8   | TSLA   | Q2 FY2026     | 2026-07-22 21:30:00Z     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.95      
9   | PG     | Q4 FY2026     | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.60      
10  | LLY    | Q2 FY2026     | 2026-08-05 14:00:00Z     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.95      
11  | LMB    | Q2 FY2026     | 2026-08-05 13:00:00Z     | Chorus Call  | Unknown      | SEC_EDGAR_8-K      | 0.95      
12  | APT    | Q2 FY2026     | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.60      
13  | DMRC   | N/A           | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.60      
14  | RELL   | Q4 FY2026     | 2026-07-23 18:00:00Z     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.95      
15  | PESI   | Q2 FY2026     | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_8-K      | 0.60      
16  | RY     | Q3 FY2026     | 2026-08-27 12:30:00Z     | In-house     | Unknown      | SEC_EDGAR_6-K      | 0.95      
17  | ENB    | Q2 FY2026     | 2026-07-31 13:00:00Z     | Q4 Inc       | Unknown      | SEC_EDGAR_8-K      | 0.95      
18  | CNR    | Q2 FY2026     | 2026-07-23 20:30:00Z     | In-house     | Unknown      | SEC_EDGAR_6-K      | 0.60      
19  | SHOP   | Q2 FY2026     | 2026-08-05 12:30:00Z     | Mux          | Unknown      | SEC_EDGAR_8-K      | 0.95      
20  | ABX    | Q2 FY2026     | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_6-K      | 0.60      
21  | T      | Q2 FY2026     | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_6-K      | 0.60      
22  | NTR    | Q2 FY2026     | NULL (Not Published)     | In-house     | Unknown      | SEC_EDGAR_6-K      | 0.60      
23  | ATD    | N/A           | NULL (Not Published)     | In-house     | Unknown      | IR_EVENTS_PAGE     | 0.60      
24  | MRU    | N/A           | NULL (Not Published)     | In-house     | Unknown      | IR_EVENTS_PAGE     | 0.60      
25  | SAP    | Q1 FY2027     | NULL (Not Published)     | Notified     | Unknown      | IR_EVENTS_PAGE     | 0.90      

--- 3. CRAWL LOG SUMMARY BY HTTP STATUS & OUTCOME ---
HTTP Status  | Outcome Description                 | Request Count
-----------------------------------------------------------------
200          | SUCCESS_CACHED                      |          412
200          | SUCCESS                             |           77
404          | FAILED                              |           39
403          | BLOCKED                             |           12

=========================================================================================================
  [OK] DATABASE AUDIT COMPLETED SUCCESSFULLY
=========================================================================================================
```

---

## 3. How a Reviewer Checks the Database

Reviewers can inspect the SQLite database directly using either Python or the SQLite CLI.

### Option A: Using the Automated Database Inspection Script
```bash
python scripts/db_report.py
```

### Option B: Using the SQLite Command Line (`sqlite3`)
```bash
# Open database
sqlite3 earnings_call.db

# View tables
sqlite> .tables
company_universe  crawl_log         event_registry

# View schema of event_registry
sqlite> .schema event_registry
```

### Option C: 3 Verification SQL Queries

#### Query 1: Verify Company Universe Count (Expected: 25 rows)
```sql
SELECT country, market_cap_bucket, COUNT(*) as count 
FROM company_universe 
GROUP BY country, market_cap_bucket;
```
*Expected Output*:
* US Large Cap: 10
* US Small Cap: 5
* TSX Large/Mid Cap: 7
* Bilingual French/English: 3
* **Total**: 25 rows

#### Query 2: Verified Earnings Date Coverage (Expected: 13 verified dates)
```sql
SELECT COUNT(*) as total_events,
       SUM(CASE WHEN call_datetime_utc IS NOT NULL THEN 1 ELSE 0 END) as verified_dates,
       SUM(CASE WHEN call_datetime_utc IS NULL THEN 1 ELSE 0 END) as null_dates
FROM event_registry
WHERE id <= 25;
```
*Expected Output*:
* Total Events: 25
* Verified Dates: 13
* Null Dates: 12

#### Query 3: Crawl Log HTTP Audit (Expected: 540 audit rows)
```sql
SELECT http_status, outcome, COUNT(*) as cnt
FROM crawl_log
GROUP BY http_status, outcome
ORDER BY cnt DESC;
```
*Expected Output*:
* 200 SUCCESS_CACHED: 412
* 200 SUCCESS: 77
* 404 FAILED: 39
* 403 BLOCKED: 12
* **Total**: 540 rows
