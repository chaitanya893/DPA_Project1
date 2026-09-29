#!/usr/bin/env python3
"""
DATABASE INSPECTION & AUDIT SCRIPT
==================================
Inspects the SQLite earnings_call.db (or PostgreSQL via DATABASE_URL) and reports:
  1. Table Names and Total Row Counts
  2. Event Registry (25 Universe Companies & Discovered Events)
  3. Crawl Log Summary by HTTP Status and Outcome
"""

import io
import os
import sys
from pathlib import Path

# Configure UTF-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text, inspect
from src.db.session import engine

def generate_db_report():
    inspector = inspect(engine)
    
    table_names = inspector.get_table_names()
    
    print("=" * 105)
    print("  EARNINGS CALL DATABASE AUDIT REPORT")
    print(f"  Database Engine: {engine.url.drivername} ({engine.url.database or 'SQLite'})")
    print("=" * 105)
    
    print("\n--- 1. TABLE NAMES & ROW COUNTS ---")
    with engine.connect() as conn:
        for t in sorted(table_names):
            res = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  * {t:<22} : {res:>4} rows")
            
        print("\n--- 2. EVENT REGISTRY (25 UNIVERSE COMPANIES) ---")
        # Query latest event per ticker from event_registry
        query = text("""
            SELECT ticker, fiscal_period, call_datetime_utc, vendor, registration_required, discovery_source, confidence
            FROM event_registry
            ORDER BY id ASC
        """)
        rows = conn.execute(query).fetchall()
        
        print(f"{'#':<3} | {'Ticker':<6} | {'Fiscal Period':<13} | {'Call Datetime (UTC)':<24} | {'Vendor':<12} | {'Reg Required':<12} | {'Discovery Source':<18} | {'Confidence':<10}")
        print("-" * 115)
        for idx, r in enumerate(rows[:25], 1):
            ticker = str(r[0] or "")
            fiscal = str(r[1] or "N/A")
            dt_str = str(r[2]) if r[2] else "NULL (Not Published)"
            if "." in dt_str and len(dt_str) > 19:
                dt_str = dt_str.split(".")[0] + "Z"
            vendor = str(r[3] or "In-house")
            reg_req = "YES" if r[4] is True else ("NO" if r[4] is False else "Unknown")
            disc_src = str(r[5] or "SEC_EDGAR")
            conf_str = f"{r[6]:.2f}" if r[6] is not None else "N/A"
            print(f"{idx:<3} | {ticker:<6} | {fiscal:<13} | {dt_str:<24} | {vendor:<12} | {reg_req:<12} | {disc_src:<18} | {conf_str:<10}")
            
        print("\n--- 3. CRAWL LOG SUMMARY BY HTTP STATUS & OUTCOME ---")
        log_query = text("""
            SELECT http_status, outcome, COUNT(*) as cnt
            FROM crawl_log
            GROUP BY http_status, outcome
            ORDER BY cnt DESC
        """)
        log_rows = conn.execute(log_query).fetchall()
        print(f"{'HTTP Status':<12} | {'Outcome Description':<35} | {'Request Count':<12}")
        print("-" * 65)
        for lr in log_rows:
            st = str(lr[0]) if lr[0] is not None else "N/A (Local)"
            print(f"{st:<12} | {str(lr[1]):<35} | {lr[2]:>12}")

    print("\n" + "=" * 105)
    print("  [OK] DATABASE AUDIT COMPLETED SUCCESSFULLY")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    generate_db_report()
