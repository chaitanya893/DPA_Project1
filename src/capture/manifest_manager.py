import csv
import datetime
import os
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Tuple

from config.settings import AUDIO_DIR, BASE_DIR
from src.db.session import SessionLocal
from src.db.models import CompanyUniverse, EventRegistry
from src.capture.audio_standardizer import get_wav_properties, compute_sha256

MANIFEST_CSV = AUDIO_DIR / "capture_manifest.csv"
FAILURES_LOG = AUDIO_DIR / "capture_failures.log"

MANIFEST_FIELDNAMES = [
    "event_id", "ticker", "fiscal_period", "audio_path",
    "capture_mode", "started_at", "ended_at", "duration_sec",
    "sample_rate", "file_size", "sha256", "failure_reason",
    "source_url", "replay_expiry_date", "url_located_by"
]

CALLS_METADATA = [
    {
        "ticker": "SHOP",
        "fiscal_period": "Q2 FY2026",
        "wav_filename": "SHOP_Q2_FY2026.wav",
        "source_url": "https://stream.mux.com/2EqBx4eDq1Ji4vU6p9Yi6JuhqueS1V3L00LjvrCRyshY.m3u8?redundant_streams=true",
        "vendor": "Mux",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "SHOP",
        "fiscal_period": "Q1 FY2026",
        "wav_filename": "SHOP_Q1_FY2026.wav",
        "source_url": "https://stream.mux.com/G1IQZwgNxKfuLrIYQyb7FEtvUJAI1KDhn01uqktkoryo.m3u8?redundant_streams=true",
        "vendor": "Mux",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q4 FY2026",
        "wav_filename": "MSFT_Q4_FY2026.wav",
        "source_url": "https://stream.event.microsoft.com/prodwe/Content/HLS/VOD/4921/6388/05a9c1bc-2b47-4f8e-9d81-7f5c2e6d7d4f/01ce826c-7b76-4d47-8b21-75c0c5abd95f/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q3 FY2026",
        "wav_filename": "MSFT_Q3_FY2026.wav",
        "source_url": "https://stream.event.microsoft.com/prodnc/Content/HLS/VOD/3719/15320/e1aac225-6f00-425f-9c28-de3867d0432b/08c5d43f-97bc-68ee-7869-23692690be7f/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q2 FY2026",
        "wav_filename": "MSFT_Q2_FY2026.wav",
        "source_url": "https://stream.event.microsoft.com/prodwe/Content/HLS/VOD/2393/8080/c28c0752-fa2c-4ddd-8a7f-d6183d9c1c01/08c5d43f-97bc-68ee-7869-23692690be7f/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q1 FY2026",
        "wav_filename": "MSFT_Q1_FY2026.wav",
        "source_url": "https://stream.event.microsoft.com/prodnc/Content/HLS/VOD/5503/18564/eff0c4ca-eba6-46ee-a75a-7089259973bf/08c5d43f-97bc-68ee-7869-23692690be7f/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q4 FY2025",
        "wav_filename": "MSFT_Q4_FY2025.wav",
        "source_url": "https://stream.event.microsoft.com/prodnc/Content/HLS/VOD/15211/13869/b6b9ca1d-3b84-45c7-98ae-193de05c3cbe/08c5d43f-97bc-68ee-7869-23692690be7f/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q3 FY2025",
        "wav_filename": "MSFT_Q3_FY2025.wav",
        "source_url": "https://stream.event.microsoft.com/prodnc/Content/HLS/LLCU/EARNNC430-ce83dced-010f-4de2-8e0b-35761de41951/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q2 FY2025",
        "wav_filename": "MSFT_Q2_FY2025.wav",
        "source_url": "https://stream.event.microsoft.com/prodnc/Content/HLS/LLCU/QEARNNC-f4615cc2-a82d-4b5a-b556-f9d1eba03e82/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q1 FY2025",
        "wav_filename": "MSFT_Q1_FY2025.wav",
        "source_url": "https://stream.event.microsoft.com/prodwe/Content/HLS/VOD/14938/4317/b46b7b85-a1d5-48b0-8086-75903c50fa7e/08c5d43f-97bc-68ee-7869-23692690be7f/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q3 FY2024",
        "wav_filename": "MSFT_Q3_FY2024.wav",
        "source_url": "https://stream.event.microsoft.com/prodwe/DynamicPackaging_ms-medius-prod-storage/HLS/asset-ea2250c8-7b2d-4a3a-81fc-d1bbb207f827/VOD003/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
    {
        "ticker": "MSFT",
        "fiscal_period": "Q2 FY2024",
        "wav_filename": "MSFT_Q2_FY2024.wav",
        "source_url": "https://stream.event.microsoft.com/prodwe/DynamicPackaging_ms-medius-prod-storage/HLS/asset-ca29e53e-850a-48cd-aae1-ea036bade8fa/VOD002/master.m3u8",
        "vendor": "Medius",
        "discovery_source": "IR_EVENTS_PAGE",
    },
]


def sync_db_and_get_event_id(ticker: str, fiscal_period: str, media_url: str, vendor: str) -> int:
    db = SessionLocal()
    try:
        cu = db.query(CompanyUniverse).filter_by(ticker=ticker).first()
        if not cu:
            return 0
        ev = db.query(EventRegistry).filter_by(ticker=ticker, fiscal_period=fiscal_period).first()
        if not ev:
            ev = EventRegistry(
                company_id=cu.id,
                ticker=ticker,
                fiscal_period=fiscal_period,
                webcast_url=media_url,
                vendor=vendor,
                discovery_source="IR_EVENTS_PAGE",
                confidence=1.0,
            )
            db.add(ev)
            db.commit()
            db.refresh(ev)
        else:
            ev.webcast_url = media_url
            ev.vendor = vendor
            db.commit()
            db.refresh(ev)
        return ev.id
    finally:
        db.close()


def clean_failure_log():
    if not FAILURES_LOG.exists():
        return
    with open(FAILURES_LOG, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    seen = set()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Normalize duplicate shopify 404s
        if stripped not in seen:
            seen.add(stripped)
            cleaned.append(stripped + "\n")
            
    with open(FAILURES_LOG, "w", encoding="utf-8") as f:
        f.writelines(cleaned)


def build_and_validate_manifest() -> Tuple[List[Dict[str, Any]], bool]:
    clean_failure_log()
    
    valid_rows = []
    all_valid = True

    for meta in CALLS_METADATA:
        ticker = meta["ticker"]
        fiscal_period = meta["fiscal_period"]
        wav_path = AUDIO_DIR / meta["wav_filename"]
        source_url = meta["source_url"]

        if not wav_path.exists():
            all_valid = False
            continue

        dur, sr, ch, bd = get_wav_properties(str(wav_path))
        sha = compute_sha256(str(wav_path))
        f_size = os.path.getsize(str(wav_path))

        # Validate Phase 2 rules
        if sr != 16000 or ch != 1 or bd != 16:
            all_valid = False
            continue
        if dur < 1200.0 or dur > 10800.0:  # 20 min to 3 h
            all_valid = False
            continue
        if f_size < 35000000:
            all_valid = False
            continue

        event_id = sync_db_and_get_event_id(ticker, fiscal_period, source_url, meta["vendor"])

        mtime = os.path.getmtime(str(wav_path))
        dt_ended = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        dt_started = datetime.datetime.fromtimestamp(mtime - dur, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        row = {
            "event_id": event_id,
            "ticker": ticker,
            "fiscal_period": fiscal_period,
            "audio_path": f"data/audio/{meta['wav_filename']}",
            "capture_mode": "direct_media_url",
            "started_at": dt_started,
            "ended_at": dt_ended,
            "duration_sec": dur,
            "sample_rate": sr,
            "file_size": f_size,
            "sha256": sha,
            "failure_reason": "",
            "source_url": source_url,
            "replay_expiry_date": "",
            "url_located_by": "auto_sniffer",
        }
        valid_rows.append(row)

    # Load and merge failure rows from previous manifest if any (preserving exact failure logs)
    final_manifest_rows = []
    
    # Read failures from existing manifest if any
    existing_failures = {}
    if MANIFEST_CSV.exists():
        try:
            with open(MANIFEST_CSV, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get("failure_reason"):
                        key = f"{r.get('ticker')}_{r.get('event_id')}"
                        existing_failures[key] = r
        except Exception:
            pass

    for r in valid_rows:
        final_manifest_rows.append(r)

    for f_row in existing_failures.values():
        if f_row.get("ticker") not in [v["ticker"] for v in valid_rows] or not f_row.get("duration_sec"):
            # Ensure new columns exist
            f_row.setdefault("fiscal_period", "")
            f_row.setdefault("audio_path", "")
            final_manifest_rows.append(f_row)

    with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        for r in final_manifest_rows:
            writer.writerow(r)

    return valid_rows, (len(valid_rows) == 12)


if __name__ == "__main__":
    valid_rows, is_complete = build_and_validate_manifest()
    print(f"Manifest updated. Valid calls count: {len(valid_rows)}/12")
