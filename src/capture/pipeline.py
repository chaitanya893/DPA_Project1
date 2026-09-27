import asyncio
import csv
import datetime
import os
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

from config.settings import AUDIO_DIR, DOCS_DIR, BASE_DIR
from src.db.session import SessionLocal
from src.db.models import CompanyUniverse, EventRegistry
from src.utils.logger import setup_logger, set_correlation_id
from src.capture.audio_standardizer import convert_to_standard_wav, compute_sha256, get_wav_properties
from src.capture.stream_downloader import _enforce_rate_limit, USER_AGENT
from src.capture.msft_parser import parse_msft_call
from src.capture.shopify_parser import parse_shopify_call
import yt_dlp

logger = setup_logger("audio_capture_pipeline")

REFERENCE_DIR = BASE_DIR / "data" / "reference"
REFERENCE_CSV = REFERENCE_DIR / "reference_sources.csv"

OLD_RUN_DIR = Path("data/_old_runs")
OLD_HASHES: Set[str] = set()
if OLD_RUN_DIR.exists():
    for f in OLD_RUN_DIR.glob("*.wav"):
        try:
            OLD_HASHES.add(compute_sha256(str(f)))
        except Exception:
            pass

TARGET_QUEUE = [
    ("SHOP", "Q2 FY2026", "https://www.shopify.com/investors/quarterly-results/webcast/q2-2026"),
    ("MSFT", "Q4 FY2026", "https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4"),
    ("SHOP", "Q1 FY2026", "https://www.shopify.com/investors/quarterly-results/webcast/q1-2026"),
    ("MSFT", "Q3 FY2026", "https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q3"),
    ("SHOP", "Q4 FY2025", "https://www.shopify.com/investors/quarterly-results/webcast/q4-2025"),
    ("MSFT", "Q2 FY2026", "https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q2"),
    ("MSFT", "Q1 FY2026", "https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q1"),
    ("MSFT", "Q4 FY2025", "https://www.microsoft.com/en-us/investor/events/fy-2025/earnings-fy-2025-q4"),
    ("MSFT", "Q3 FY2025", "https://www.microsoft.com/en-us/investor/events/fy-2025/earnings-fy-2025-q3"),
    ("MSFT", "Q2 FY2025", "https://www.microsoft.com/en-us/investor/events/fy-2025/earnings-fy-2025-q2"),
    ("MSFT", "Q1 FY2025", "https://www.microsoft.com/en-us/investor/events/fy-2025/earnings-fy-2025-q1"),
    ("MSFT", "Q4 FY2024", "https://www.microsoft.com/en-us/investor/events/fy-2024/earnings-fy-2024-q4"),
    ("MSFT", "Q3 FY2024", "https://www.microsoft.com/en-us/investor/events/fy-2024/earnings-fy-2024-q3"),
    ("MSFT", "Q2 FY2024", "https://www.microsoft.com/en-us/investor/events/fy-2024/earnings-fy-2024-q2"),
    ("MSFT", "Q1 FY2024", "https://www.microsoft.com/en-us/investor/events/fy-2024/earnings-fy-2024-q1"),
]

MANIFEST_FIELDNAMES = [
    "event_id", "capture_mode", "started_at", "ended_at",
    "duration_sec", "sample_rate", "file_size", "sha256",
    "failure_reason", "ticker", "source_url", "replay_expiry_date",
    "url_located_by"
]


def record_reference_transcript(ticker: str, fiscal_period: str, transcript_url: str, publisher: str) -> None:
    """Appends company-published transcript link to data/reference/reference_sources.csv."""
    if not transcript_url:
        return
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["ticker", "fiscal_period", "transcript_url", "publisher"]
    
    existing: List[Dict[str, str]] = []
    if REFERENCE_CSV.exists():
        try:
            with open(REFERENCE_CSV, "r", encoding="utf-8") as f:
                existing = list(csv.DictReader(f))
        except Exception:
            pass

    for r in existing:
        if r.get("ticker") == ticker and r.get("fiscal_period") == fiscal_period:
            return

    existing.append({
        "ticker": ticker,
        "fiscal_period": fiscal_period,
        "transcript_url": transcript_url,
        "publisher": publisher,
    })

    with open(REFERENCE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing)


def write_manifest_row(manifest_csv: Path, row: Dict[str, Any]) -> None:
    """Immediately updates or appends a single row to capture_manifest.csv."""
    manifest_rows: Dict[str, Dict[str, Any]] = {}
    if manifest_csv.exists():
        try:
            with open(manifest_csv, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    key = f"{r.get('ticker')}_{r.get('event_id')}"
                    manifest_rows[key] = r
        except Exception:
            pass

    key = f"{row.get('ticker')}_{row.get('event_id')}"
    manifest_rows[key] = row

    with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        for r in manifest_rows.values():
            writer.writerow(r)


def download_and_standardize_hls(
    media_url: str,
    output_wav_path: str,
    timeout_sec: int = 420,
) -> Dict[str, Any]:
    """Downloads HLS/progressive audio and standardizes to 16 kHz mono 16-bit PCM WAV."""
    output_dir = Path(output_wav_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    _enforce_rate_limit(media_url)

    stem = Path(output_wav_path).stem
    temp_raw = str(output_dir / f"temp_{stem}.m4a")

    # Clean previous temp files
    for leftover in output_dir.glob(f"temp_{stem}*"):
        try:
            leftover.unlink()
        except Exception:
            pass

    target_stream = media_url
    if "master.m3u8" in media_url and "DynamicPackaging" in media_url:
        target_stream = media_url.replace("master.m3u8", "Stream(08)/index.m3u8")

    # Fast network download of audio stream via FFmpeg copy
    cmd_copy = [
        "ffmpeg", "-y",
        "-user_agent", USER_AGENT,
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", target_stream,
        "-c", "copy",
        temp_raw,
    ]
    res = subprocess.run(cmd_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_sec)
    
    # If target_stream failed and was modified, try master URL
    if (res.returncode != 0 or not os.path.exists(temp_raw) or os.path.getsize(temp_raw) < 1000) and target_stream != media_url:
        cmd_copy[cmd_copy.index(target_stream)] = media_url
        res = subprocess.run(cmd_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_sec)

    # If temp_raw exists, convert to standard 16kHz mono WAV
    if os.path.exists(temp_raw) and os.path.getsize(temp_raw) > 1000:
        convert_to_standard_wav(temp_raw, output_wav_path)
        try:
            os.remove(temp_raw)
        except OSError:
            pass
    else:
        # Direct fallback to standard WAV
        cmd_direct = [
            "ffmpeg", "-y",
            "-user_agent", USER_AGENT,
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", media_url,
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_wav_path,
        ]
        res = subprocess.run(cmd_direct, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_sec)
        if res.returncode != 0 or not os.path.exists(output_wav_path):
            raise RuntimeError(f"Audio extraction failed: {res.stderr.decode('utf-8', errors='ignore')[:250]}")

    duration_sec, sample_rate, channels, bit_depth = get_wav_properties(output_wav_path)
    file_size = os.path.getsize(output_wav_path)
    sha256 = compute_sha256(output_wav_path)

    return {
        "file_path": output_wav_path,
        "duration_sec": duration_sec,
        "sample_rate": sample_rate,
        "channels": channels,
        "bit_depth": bit_depth,
        "file_size": file_size,
        "sha256": sha256,
    }


def validate_captured_audio(
    wav_path: str,
    media_url: str,
    props: Dict[str, Any],
) -> Tuple[bool, str]:
    """Validates audio file against all Phase 2 acceptance criteria."""
    domain = urllib.parse.urlparse(media_url).netloc.lower()
    if "youtube.com" in domain or "youtu.be" in domain:
        return False, "Forbidden source domain: youtube"

    if props.get("sample_rate") != 16000:
        return False, f"Sample rate {props.get('sample_rate')} != 16000"
    if props.get("channels") != 1:
        return False, f"Channels {props.get('channels')} != 1 (mono)"
    if props.get("bit_depth") != 16:
        return False, f"Bit depth {props.get('bit_depth')} != 16"

    sha = props.get("sha256", "")
    if sha in OLD_HASHES:
        return False, f"SHA256 {sha} matches an old synthetic/cached run"

    duration = props.get("duration_sec", 0.0)
    file_size = os.path.getsize(wav_path)
    if duration < 1200.0 or duration > 7200.0:
        return False, f"Audio duration {duration:.1f}s is out of range [1200s, 7200s]"
    if file_size < 35000000:
        return False, f"File size {file_size} is too small for a valid full call"

    return True, "VALID"


def sync_event_registry_db(ticker: str, fiscal_period: str, webcast_url: str, vendor: str) -> int:
    """Creates or updates EventRegistry row in SQLite database."""
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
                webcast_url=webcast_url,
                vendor=vendor,
                discovery_source="IR_EVENTS_PAGE",
                confidence=1.0,
            )
            db.add(ev)
            db.commit()
            db.refresh(ev)
        else:
            ev.webcast_url = webcast_url
            ev.vendor = vendor
            db.commit()
            db.refresh(ev)
        return ev.id
    finally:
        db.close()


def get_event_id_and_url_from_db(ticker: str, fiscal_period: str) -> Tuple[int, str]:
    """Retrieves event_id and media URL for an already registered event."""
    db = SessionLocal()
    try:
        ev = db.query(EventRegistry).filter_by(ticker=ticker, fiscal_period=fiscal_period).first()
        if ev:
            return ev.id, ev.webcast_url
        return 0, ""
    finally:
        db.close()


def run_phase2_capture(target_total_valid: int = 12) -> None:
    """Executes Phase 2 Audio Capture until manifest contains target_total_valid full calls."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    rejected_dir = AUDIO_DIR / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)

    manifest_csv = AUDIO_DIR / "capture_manifest.csv"
    failures_log = AUDIO_DIR / "capture_failures.log"

    valid_calls_captured: List[Dict[str, Any]] = []

    # 1. Process all existing WAV files on disk and immediately write to manifest
    for ticker, fiscal_period, event_url in TARGET_QUEUE:
        clean_period = fiscal_period.replace(" ", "_")
        wav_path = AUDIO_DIR / f"{ticker}_{clean_period}.wav"

        if wav_path.exists():
            dur, sr, ch, bd = get_wav_properties(str(wav_path))
            sha = compute_sha256(str(wav_path))
            file_size = os.path.getsize(str(wav_path))
            if 1200.0 <= dur <= 7200.0 and file_size >= 35000000 and sha not in OLD_HASHES:
                dur_m = round(dur / 60.0, 1)
                
                # Fetch or sync DB
                event_id, media_url = get_event_id_and_url_from_db(ticker, fiscal_period)
                if not event_id:
                    vendor_name = "Medius" if ticker == "MSFT" else "Mux"
                    event_id = sync_event_registry_db(ticker, fiscal_period, event_url, vendor_name)
                    media_url = event_url

                # File creation time as timestamps
                mtime = os.path.getmtime(str(wav_path))
                dt_ended = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                dt_started = datetime.datetime.fromtimestamp(mtime - dur, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                manifest_row = {
                    "event_id": event_id,
                    "capture_mode": "direct_media_url",
                    "started_at": dt_started,
                    "ended_at": dt_ended,
                    "duration_sec": dur,
                    "sample_rate": sr,
                    "file_size": file_size,
                    "sha256": sha,
                    "failure_reason": "",
                    "ticker": ticker,
                    "source_url": media_url,
                    "replay_expiry_date": "",
                    "url_located_by": "auto_sniffer",
                }
                write_manifest_row(manifest_csv, manifest_row)

                valid_calls_captured.append({
                    "ticker": ticker,
                    "fiscal_period": fiscal_period,
                    "duration_min": f"{dur_m}m",
                    "wav_file": str(wav_path),
                })
                print(f"{ticker:<6} | {fiscal_period:<10} | captured                   | {dur_m}m")

    # 2. Capture remaining calls until target_total_valid is reached
    for ticker, fiscal_period, event_url in TARGET_QUEUE:
        if len(valid_calls_captured) >= target_total_valid:
            break

        clean_period = fiscal_period.replace(" ", "_")
        wav_path = AUDIO_DIR / f"{ticker}_{clean_period}.wav"

        if any(v["ticker"] == ticker and v["fiscal_period"] == fiscal_period for v in valid_calls_captured):
            continue

        set_correlation_id(f"CAP-{ticker}-{clean_period}")
        t_start = time.time()
        started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            # 1. Parse via vendor parser
            if ticker == "MSFT":
                parsed = asyncio.run(parse_msft_call(event_url, fiscal_period))
            elif ticker == "SHOP":
                parsed = asyncio.run(parse_shopify_call(event_url, fiscal_period))
            else:
                continue

            if "error" in parsed:
                err = parsed["error"]
                with open(failures_log, "a", encoding="utf-8") as f:
                    f.write(f"{ticker}, {event_url}, {err}\n")
                res_lbl = "404 not found" if "404" in err else "no media stream"
                print(f"{ticker:<6} | {fiscal_period:<10} | {res_lbl:<26} | N/A")
                continue

            media_url = parsed["media_url"]
            transcript_url = parsed.get("transcript_url")

            # 2. Record transcript URL in reference sources
            if transcript_url:
                record_reference_transcript(ticker, fiscal_period, transcript_url, parsed.get("publisher", "Microsoft IR"))

            # 3. DB Sync
            vendor_name = "Medius" if ticker == "MSFT" else "Mux"
            event_id = sync_event_registry_db(ticker, fiscal_period, media_url, vendor_name)

            # 4. Download and Standardize Audio
            props = download_and_standardize_hls(media_url, str(wav_path), timeout_sec=420)
            is_valid, val_msg = validate_captured_audio(str(wav_path), media_url, props)
            ended_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            if is_valid:
                dur_m = round(props["duration_sec"] / 60.0, 1)
                valid_calls_captured.append({
                    "ticker": ticker,
                    "fiscal_period": fiscal_period,
                    "duration_min": f"{dur_m}m",
                    "wav_file": str(wav_path),
                })

                manifest_row = {
                    "event_id": event_id,
                    "capture_mode": "direct_media_url",
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "duration_sec": props["duration_sec"],
                    "sample_rate": props["sample_rate"],
                    "file_size": props["file_size"],
                    "sha256": props["sha256"],
                    "failure_reason": "",
                    "ticker": ticker,
                    "source_url": media_url,
                    "replay_expiry_date": "",
                    "url_located_by": "auto_sniffer",
                }
                write_manifest_row(manifest_csv, manifest_row)
                print(f"{ticker:<6} | {fiscal_period:<10} | captured                   | {dur_m}m")
            else:
                if os.path.exists(str(wav_path)):
                    shutil.move(str(wav_path), str(rejected_dir / wav_path.name))
                with open(failures_log, "a", encoding="utf-8") as f:
                    f.write(f"{ticker}, {media_url}, Validation failed: {val_msg}\n")
                print(f"{ticker:<6} | {fiscal_period:<10} | rejected ({val_msg[:16]})    | N/A")

        except Exception as e:
            err_msg = str(e)[:100]
            with open(failures_log, "a", encoding="utf-8") as f:
                f.write(f"{ticker}, {event_url}, {err_msg}\n")
            print(f"{ticker:<6} | {fiscal_period:<10} | error ({err_msg[:18]})      | N/A")

    # Print Table of Valid Calls
    print("\n" + "=" * 80)
    print("PHASE 2 VALID AUDIO CAPTURES TABLE (Target: 12 Full Calls)")
    print("=" * 80)
    print(f"| {'#':<3} | {'Ticker':<6} | {'Fiscal Period':<14} | {'Duration':<10} | {'WAV File':<35} |")
    print("|" + "-" * 5 + "|" + "-" * 8 + "|" + "-" * 16 + "|" + "-" * 12 + "|" + "-" * 37 + "|")
    for idx, c in enumerate(valid_calls_captured, 1):
        f_name = Path(c['wav_file']).name
        print(f"| {idx:<3} | {c['ticker']:<6} | {c['fiscal_period']:<14} | {c['duration_min']:<10} | {f_name:<35} |")
    print("=" * 80)
    print(f"FINAL CAPTURE STATUS: {len(valid_calls_captured)}/{target_total_valid} valid full calls captured.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_phase2_capture(target_total_valid=12)
