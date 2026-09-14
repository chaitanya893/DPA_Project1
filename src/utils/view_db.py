import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.db.session import SessionLocal, init_db
from src.db.models import CompanyUniverse, EventRegistry, CrawlLog


def display_database_summary():
    """Prints a clean, human-readable summary of all tables and records in the database."""
    init_db()
    db = SessionLocal()

    try:
        companies = db.query(CompanyUniverse).all()
        events = db.query(EventRegistry).all()
        logs = db.query(CrawlLog).all()

        print("\n" + "=" * 80)
        print("  [DATABASE REPORT] Earnings Call Capture Database Inspection")
        print("=" * 80)

        print(f"\n1. COMPANY UNIVERSE TABLE (`company_universe`) - Total Records: {len(companies)}")
        print("-" * 80)
        print(f"{'ID':<4} | {'Ticker':<6} | {'Exchange':<8} | {'Country':<7} | {'Market Cap':<10} | {'Company Name'}")
        print("-" * 80)
        for c in companies[:10]:
            print(f"{c.id:<4} | {c.ticker:<6} | {c.exchange:<8} | {c.country:<7} | {c.market_cap_bucket:<10} | {c.company_name}")
        if len(companies) > 10:
            print(f"... and {len(companies) - 10} more companies.")

        print(f"\n2. EVENT REGISTRY TABLE (`event_registry`) - Total Records: {len(events)}")
        print("-" * 80)
        print(f"{'ID':<4} | {'Ticker':<6} | {'Fiscal Period':<12} | {'Vendor':<15} | {'Source':<18} | {'Confidence'}")
        print("-" * 80)
        for e in events[:10]:
            print(f"{e.id:<4} | {e.ticker:<6} | {e.fiscal_period:<12} | {(e.vendor or 'Custom')[:14]:<15} | {e.discovery_source[:17]:<18} | {e.confidence:.2f}")
        if len(events) > 10:
            print(f"... and {len(events) - 10} more earnings call events.")

        print(f"\n3. CRAWL LOG TABLE (`crawl_log`) - Total Attempts: {len(logs)}")
        print("-" * 80)
        print(f"Total network & scraper attempts logged: {len(logs)}")
        print("=" * 80 + "\n")

    finally:
        db.close()


def ensure_notebook_exists():
    """Generates the Assignment 1 exploratory walkthrough notebook in notebooks/."""
    import json
    import os
    from pathlib import Path
    
    nb_dir = Path("notebooks")
    nb_dir.mkdir(parents=True, exist_ok=True)
    nb_path = nb_dir / "earnings_call_pipeline_walkthrough.ipynb"
    
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Assignment 1: Corporate Earnings Call Pipeline & Accuracy Benchmarking\n",
                "\n",
                "This walkthrough notebook demonstrates the end-to-end open-source pipeline:\n",
                "- **Phase 0**: Target Universe (25 Companies) & Source Compliance\n",
                "- **Phase 1**: SEC EDGAR & IR Event Discovery Pipeline\n",
                "- **Phase 2**: Audio Capture & 16kHz Mono 16-bit PCM WAV Standardization\n",
                "- **Phase 3**: Streaming ASR Transcription, Diarization & Section Split\n",
                "- **Phase 4**: Financial Normalizer, Levenshtein WER/CER, 7-Class Entity Evaluation & Cost Model\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "import json\n",
                "from config.settings import UNIVERSE_CSV_PATH, AUDIO_DIR, TRANSCRIPTS_DIR\n",
                "from src.benchmark.evaluator import run_benchmark_evaluation\n",
                "\n",
                "# 1. Load 25-Company Master Universe\n",
                "universe_df = pd.read_csv(UNIVERSE_CSV_PATH)\n",
                "print(f'Total Companies Monitored: {len(universe_df)}')\n",
                "universe_df.head(10)\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 2. Inspect Audio Capture Manifest\n",
                "manifest_df = pd.read_csv(AUDIO_DIR / 'capture_manifest.csv')\n",
                "print(f'Captured Audio Files: {len(manifest_df)}')\n",
                "manifest_df[['ticker', 'fiscal_period', 'duration_sec', 'sample_rate', 'channels', 'bit_depth', 'capture_status']].head(10)\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 3. Run Benchmark Evaluation\n",
                "bench_res = run_benchmark_evaluation()\n",
                "for metric, value in bench_res['summary'].items():\n",
                "    print(f'{metric}: {value}')\n"
            ]
        }
    ]
    
    nb_doc = {
        "cells": cells,
        "metadata": {"language_info": {"name": "python"}},
        "nbformat": 4,
        "nbformat_minor": 2
    }
    
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb_doc, f, indent=2)


if __name__ == "__main__":
    ensure_notebook_exists()
    display_database_summary()
