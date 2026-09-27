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
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import yt_dlp

from config.settings import AUDIO_DIR, DOCS_DIR
from src.db.session import SessionLocal
from src.db.models import CompanyUniverse, EventRegistry
from src.utils.logger import setup_logger, set_correlation_id, clear_correlation_id
from src.capture.audio_standardizer import convert_to_standard_wav, compute_sha256, get_wav_properties
from src.capture.stream_downloader import _enforce_rate_limit, USER_AGENT

logger = setup_logger("audio_capture_pipeline")

TARGET_COMPANIES = [
    "JNJ", "LLY", "TSLA", "RELL", "LMB", "ENB", "CNR",
    "ATD", "MRU", "SAP", "WMT", "NTR", "T", "PESI",
    "APT", "DMRC", "GOOGL", "PG", "ABX"
]

SKIPPED_COMPANIES = {"AAPL", "MSFT", "RY", "JPM"}

OLD_RUN_DIR = Path("data/_old_runs")
OLD_HASHES: Set[str] = set()
if OLD_RUN_DIR.exists():
    for f in OLD_RUN_DIR.glob("*.wav"):
        try:
            OLD_HASHES.add(compute_sha256(str(f)))
        except Exception:
            pass


def probe_media_duration_ffprobe(media_url: str, timeout_sec: int = 15) -> float:
    """Uses ffprobe to inspect remote media duration without full download."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-user_agent", USER_AGENT,
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            media_url
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_sec)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return 0.0


def extract_quarter_keywords(fiscal_period: str) -> List[str]:
    """Generates keywords matching the target earnings call quarter."""
    fp = fiscal_period.lower()
    q_num = "2"
    if "q1" in fp or "first" in fp:
        q_num = "1"
    elif "q3" in fp or "third" in fp:
        q_num = "3"
    elif "q4" in fp or "fourth" in fp:
        q_num = "4"

    q_word = {"1": "first", "2": "second", "3": "third", "4": "fourth"}[q_num]
    return [
        f"q{q_num}",
        f"quarter {q_num}",
        f"{q_word} quarter",
        f"q{q_num} 202",
        f"q{q_num} fy",
        f"q{q_num} results",
        f"q{q_num} earnings",
        f"quarter_{q_num}",
    ]


async def sniff_media_url_playwright(
    start_url: str,
    fiscal_period: str,
    page_timeout_sec: int = 25,
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Opens starting webcast / IR URL in Playwright, follows links matching the SAME call
    up to 2 hops, clicks playback controls, and captures direct media streams.
    """
    if not start_url or not start_url.startswith("http"):
        return None, None, "Invalid or missing URL"

    domain = urllib.parse.urlparse(start_url).netloc.lower()
    if "youtube.com" in domain or "youtu.be" in domain:
        return None, None, "YouTube is forbidden by compliance policy (ToS Section 5.B)"

    _enforce_rate_limit(start_url)
    discovered_media: List[str] = []
    q_keywords = extract_quarter_keywords(fiscal_period)

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-http2", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent=f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 ({USER_AGENT})"
            )
            page = await context.new_page()

            def on_response(response):
                u = response.url
                ct = response.headers.get("content-type", "").lower()
                if "youtube.com" in u.lower() or "youtu.be" in u.lower():
                    return
                if any(t in ct for t in ["audio/", "video/", "application/x-mpegurl", "application/vnd.apple.mpegurl"]):
                    if not any(x in u.lower() for x in [".js", ".css", ".png", ".jpg", ".svg", "beacon", "telemetry", "analytics", "tracking", "icon"]):
                        discovered_media.append(u)
                elif any(u.lower().endswith(ext) or ext in u.lower() for ext in [".m3u8", ".mp3", ".mp4", ".m4a", ".aac", ".wav"]):
                    if not any(x in u.lower() for x in [".js", ".css", ".png", ".jpg", ".svg", "beacon", "telemetry", "analytics"]):
                        discovered_media.append(u)

            page.on("response", on_response)

            visited_urls: Set[str] = set()
            queue: List[Tuple[str, int]] = [(start_url, 0)]
            last_reason = f"no media stream found at {start_url}"

            while queue and len(visited_urls) < 4:
                curr_url, hop = queue.pop(0)
                if curr_url in visited_urls:
                    continue
                visited_urls.add(curr_url)

                _enforce_rate_limit(curr_url)
                try:
                    await page.goto(curr_url, wait_until="domcontentloaded", timeout=page_timeout_sec * 1000)
                except Exception as e:
                    last_reason = f"Navigation failed at {curr_url}: {str(e)[:80]}"
                    continue

                await page.wait_for_timeout(2500)

                # Check for mandatory registration forms
                content = await page.content()
                content_lower = content.lower()
                if any(term in content_lower for term in ["please register", "registration required", "sign in to view", "register to attend", "register for webcast"]):
                    inputs = await page.query_selector_all("input[type='text'], input[type='email'], input[type='password']")
                    if len(inputs) >= 2:
                        return None, None, f"registration form required at {curr_url}"

                # Check direct DOM media tags
                soup = BeautifulSoup(content, "html.parser")
                for tag in soup.find_all(["audio", "video", "source", "a"]):
                    src = tag.get("src") or tag.get("href")
                    if src:
                        full_src = urllib.parse.urljoin(curr_url, src)
                        if any(full_src.lower().endswith(ext) for ext in [".m3u8", ".mp3", ".mp4", ".m4a", ".aac", ".wav"]):
                            if "youtube" not in full_src.lower():
                                discovered_media.append(full_src)

                # Click play / listen / webcast buttons
                play_buttons = await page.query_selector_all(
                    "button[aria-label*='play' i], button[aria-label*='listen' i], button[aria-label*='replay' i], button[aria-label*='webcast' i], .vjs-big-play-button, .play-button, .vjs-play-control, button.play, a[href*='webcast'], a[aria-label*='play' i]"
                )
                for b in play_buttons[:2]:
                    try:
                        if await b.is_visible():
                            await b.click(timeout=1500)
                            await page.wait_for_timeout(3000)
                    except Exception:
                        pass

                # Inspect discovered media
                valid_candidates = []
                for m in discovered_media:
                    if any(x in m.lower() for x in ["brochure", "promo", "teaser", "preview", "banner"]):
                        continue
                    if any(m.lower().endswith(ext) for ext in [".mp3", ".mp4", ".m4a", ".wav"]):
                        dur = probe_media_duration_ffprobe(m)
                        if 0 < dur < 1200.0:
                            continue
                    valid_candidates.append(m)

                if valid_candidates:
                    best_url = valid_candidates[0]
                    for m in valid_candidates:
                        if ".m3u8" in m.lower() or ".mp3" in m.lower():
                            best_url = m
                            break
                    mode = "direct_media_url" if (".m3u8" in best_url or ".mp3" in best_url or ".mp4" in best_url) else "archived_replay_download"
                    return best_url, mode, "SUCCESS"

                if any(term in content_lower for term in ["replay has expired", "webcast is no longer available", "event has concluded"]):
                    last_reason = f"replay expired at {curr_url}"

                # If hop < 2, look for sub-links matching the target quarter call
                if hop < 2:
                    for a in soup.find_all("a"):
                        txt = a.get_text(separator=" ", strip=True).lower()
                        href = a.get("href", "")
                        if not href or href.startswith("#") or href.startswith("javascript:"):
                            continue
                        if any(k in txt or k in href.lower() for k in q_keywords) and any(
                            k in txt or k in href.lower() for k in ["webcast", "listen", "replay", "call", "earnings", "audio", "event"]
                        ):
                            full_child = urllib.parse.urljoin(curr_url, href)
                            if not any(full_child.lower().endswith(ext) for ext in [".pdf", ".xlsx", ".zip"]):
                                if full_child not in visited_urls and len(queue) < 3:
                                    queue.append((full_child, hop + 1))

            return None, None, last_reason

        except Exception as e:
            return None, None, f"error at {start_url}: {str(e)[:80]}"
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass


def download_and_standardize(
    media_url: str,
    output_wav_path: str,
    timeout_sec: int = 150,
) -> Dict[str, Any]:
    """Downloads audio from direct media URL via FFmpeg or yt-dlp and standardizes to 16kHz mono 16-bit PCM WAV."""
    output_dir = Path(output_wav_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    _enforce_rate_limit(media_url)

    # 1. If .m3u8 HLS stream, use yt-dlp
    if ".m3u8" in media_url.lower():
        temp_raw = str(output_dir / f"temp_{Path(output_wav_path).stem}.m4a")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": temp_raw,
            "quiet": True,
            "no_warnings": True,
            "user_agent": USER_AGENT,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([media_url])
            if os.path.exists(temp_raw):
                convert_to_standard_wav(temp_raw, output_wav_path)
                try:
                    os.remove(temp_raw)
                except OSError:
                    pass
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
        except Exception as e:
            logger.warning(f"yt-dlp download failed for {media_url}: {e}; falling back to ffmpeg")

    # 2. Direct FFmpeg conversion
    cmd = [
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
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_sec)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed (code {res.returncode}): {res.stderr.decode('utf-8', errors='ignore')[:250]}")

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
    if duration < 1200.0:
        return False, f"Audio duration {duration:.1f}s is less than full call requirement (1200s)"

    return True, "VALID"


def load_replay_sources() -> Dict[str, Dict[str, Any]]:
    """Loads optional config/replay_sources.csv if present."""
    csv_path = Path("config/replay_sources.csv")
    sources: Dict[str, Dict[str, Any]] = {}
    if csv_path.exists():
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    t = row.get("ticker", "").strip().upper()
                    if t:
                        sources[t] = {
                            "replay_page_url": row.get("replay_page_url", "").strip(),
                            "media_url": row.get("media_url", "").strip(),
                            "registration_required": row.get("registration_required", "").strip().lower() in ("true", "1", "yes"),
                        }
        except Exception as e:
            logger.warning(f"Error loading replay_sources.csv: {e}")
    return sources


async def capture_single_company(
    ticker: str,
    ev: Dict[str, Any],
    replay_sources: Dict[str, Dict[str, Any]],
    output_wav: str,
    rejected_dir: Path,
) -> Dict[str, Any]:
    """Orchestrates capture for a single company asynchronously."""
    event_id = ev["id"]
    fiscal_period = ev["fiscal_period"] or "Q2 FY2026"
    primary_url = ev["webcast_url"] or ev["ir_page_url"]
    ir_page_url = ev["ir_page_url"]

    # Check replay_sources.csv if available
    rs = replay_sources.get(ticker)
    if rs:
        if rs.get("registration_required"):
            src_dom = urllib.parse.urlparse(rs.get("replay_page_url") or primary_url).netloc
            return {
                "ticker": ticker,
                "event_id": event_id,
                "result": "registration form required",
                "duration_min": "N/A",
                "source_domain": src_dom,
                "is_valid": False,
                "manifest_row": {
                    "event_id": event_id,
                    "capture_mode": "direct_media_url",
                    "started_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "ended_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "duration_sec": 0.0,
                    "sample_rate": 0,
                    "file_size": 0,
                    "sha256": "",
                    "failure_reason": f"registration form required at {rs.get('replay_page_url') or primary_url}",
                    "ticker": ticker,
                    "source_url": primary_url,
                    "replay_expiry_date": "",
                },
                "failure_entry": f"{ticker}, {primary_url}, registration form required",
            }
        if rs.get("media_url"):
            primary_url = rs["media_url"]
        elif rs.get("replay_page_url"):
            primary_url = rs["replay_page_url"]

    started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Determine media URL
    media_url: Optional[str] = None
    mode: Optional[str] = None
    status: str = ""

    if primary_url and any(primary_url.lower().endswith(ext) for ext in [".m3u8", ".mp3", ".mp4", ".m4a", ".aac"]):
        media_url = primary_url
        mode = "direct_media_url"
        status = "SUCCESS"
    else:
        media_url, mode, status = await sniff_media_url_playwright(primary_url, fiscal_period=fiscal_period, page_timeout_sec=25)
        if not media_url and ir_page_url and ir_page_url != primary_url:
            media_url, mode, status = await sniff_media_url_playwright(ir_page_url, fiscal_period=fiscal_period, page_timeout_sec=20)

    domain_for_log = urllib.parse.urlparse(media_url or primary_url).netloc
    ended_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not media_url:
        res_label = "registration form required" if "registration" in status.lower() else ("replay expired" if "expired" in status.lower() else "no media stream")
        return {
            "ticker": ticker,
            "event_id": event_id,
            "result": res_label,
            "duration_min": "N/A",
            "source_domain": domain_for_log,
            "is_valid": False,
            "manifest_row": {
                "event_id": event_id,
                "capture_mode": mode or "direct_media_url",
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_sec": 0.0,
                "sample_rate": 0,
                "file_size": 0,
                "sha256": "",
                "failure_reason": status,
                "ticker": ticker,
                "source_url": primary_url,
                "replay_expiry_date": ev["replay_expiry_date"].strftime("%Y-%m-%d") if ev["replay_expiry_date"] else "",
            },
            "failure_entry": f"{ticker}, {primary_url}, {status}",
        }

    # 2. Download and Standardize
    try:
        props = download_and_standardize(media_url, output_wav, timeout_sec=150)
        is_valid, val_msg = validate_captured_audio(output_wav, media_url, props)
        ended_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if is_valid:
            dur_min = round(props["duration_sec"] / 60.0, 1)
            return {
                "ticker": ticker,
                "event_id": event_id,
                "result": "captured",
                "duration_min": f"{dur_min}m",
                "source_domain": domain_for_log,
                "is_valid": True,
                "manifest_row": {
                    "event_id": event_id,
                    "capture_mode": mode,
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "duration_sec": props["duration_sec"],
                    "sample_rate": props["sample_rate"],
                    "file_size": props["file_size"],
                    "sha256": props["sha256"],
                    "failure_reason": "",
                    "ticker": ticker,
                    "source_url": media_url,
                    "replay_expiry_date": ev["replay_expiry_date"].strftime("%Y-%m-%d") if ev["replay_expiry_date"] else "",
                },
                "failure_entry": None,
            }
        else:
            if os.path.exists(output_wav):
                shutil.move(output_wav, str(rejected_dir / Path(output_wav).name))
            return {
                "ticker": ticker,
                "event_id": event_id,
                "result": f"rejected ({val_msg[:16]})",
                "duration_min": "N/A",
                "source_domain": domain_for_log,
                "is_valid": False,
                "manifest_row": {
                    "event_id": event_id,
                    "capture_mode": mode,
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "duration_sec": 0.0,
                    "sample_rate": 0,
                    "file_size": 0,
                    "sha256": "",
                    "failure_reason": val_msg,
                    "ticker": ticker,
                    "source_url": media_url,
                    "replay_expiry_date": "",
                },
                "failure_entry": f"{ticker}, {media_url}, Validation failed: {val_msg}",
            }
    except Exception as e:
        err_msg = str(e)[:100]
        return {
            "ticker": ticker,
            "event_id": event_id,
            "result": f"error ({err_msg[:16]})",
            "duration_min": "N/A",
            "source_domain": domain_for_log,
            "is_valid": False,
            "manifest_row": {
                "event_id": event_id,
                "capture_mode": mode,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_sec": 0.0,
                "sample_rate": 0,
                "file_size": 0,
                "sha256": "",
                "failure_reason": err_msg,
                "ticker": ticker,
                "source_url": media_url,
                "replay_expiry_date": "",
            },
            "failure_entry": f"{ticker}, {media_url}, {err_msg}",
        }


def run_phase2_capture(target_limit: int = 7, per_company_timeout_sec: int = 180) -> None:
    """
    Executes Phase 2 Audio Capture with a hard per-company timeout (default 180s).
    Merges capture_manifest.csv and capture_failures.log without overwriting existing valid rows.
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    rejected_dir = AUDIO_DIR / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)

    manifest_csv = AUDIO_DIR / "capture_manifest.csv"
    failures_log = AUDIO_DIR / "capture_failures.log"

    # Load existing manifest rows
    manifest_by_ticker: Dict[str, Dict[str, Any]] = {}
    fieldnames = [
        "event_id", "capture_mode", "started_at", "ended_at",
        "duration_sec", "sample_rate", "file_size", "sha256",
        "failure_reason", "ticker", "source_url", "replay_expiry_date"
    ]
    if manifest_csv.exists():
        try:
            with open(manifest_csv, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("ticker"):
                        manifest_by_ticker[row["ticker"]] = row
        except Exception:
            pass

    replay_sources = load_replay_sources()

    db = SessionLocal()
    try:
        events = db.query(EventRegistry).join(CompanyUniverse).all()
        event_data_by_ticker = {}
        for e in events:
            event_data_by_ticker[e.ticker] = {
                "id": e.id,
                "ticker": e.ticker,
                "fiscal_period": e.fiscal_period,
                "webcast_url": e.webcast_url,
                "ir_page_url": e.company.ir_page_url if e.company else None,
                "replay_expiry_date": e.replay_expiry_date,
            }
    finally:
        db.close()

    newly_captured_count = 0
    failure_entries: List[str] = []

    print("\n" + "=" * 90)
    print(f"PHASE 2 AUTOMATIC AUDIO CAPTURE (Target: {target_limit} new full calls, Timeout: {per_company_timeout_sec}s/company)")
    print("=" * 90)

    for ticker in TARGET_COMPANIES:
        if ticker in SKIPPED_COMPANIES:
            continue

        if newly_captured_count >= target_limit:
            print(f"Reached target of {target_limit} newly captured calls. Stopping.")
            break

        if ticker not in event_data_by_ticker:
            continue

        ev = event_data_by_ticker[ticker]
        fiscal_period = ev["fiscal_period"] or "Q2 FY2026"
        clean_period = fiscal_period.replace(" ", "_")
        output_wav = str(AUDIO_DIR / f"{ticker}_{clean_period}.wav")
        primary_url = ev["webcast_url"] or ev["ir_page_url"]
        domain_for_log = urllib.parse.urlparse(primary_url).netloc

        set_correlation_id(f"CAP-{ticker}")

        try:
            res = asyncio.run(
                asyncio.wait_for(
                    capture_single_company(
                        ticker=ticker,
                        ev=ev,
                        replay_sources=replay_sources,
                        output_wav=output_wav,
                        rejected_dir=rejected_dir,
                    ),
                    timeout=float(per_company_timeout_sec)
                )
            )

            manifest_by_ticker[ticker] = res["manifest_row"]
            if res.get("failure_entry"):
                failure_entries.append(res["failure_entry"])
            if res.get("is_valid"):
                newly_captured_count += 1

            print(f"{ticker:<6} | {res['result']:<26} | {res['duration_min']:<12} | {res['source_domain']}")

        except asyncio.TimeoutError:
            started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            manifest_by_ticker[ticker] = {
                "event_id": ev["id"],
                "capture_mode": "direct_media_url",
                "started_at": started_at,
                "ended_at": started_at,
                "duration_sec": 0.0,
                "sample_rate": 0,
                "file_size": 0,
                "sha256": "",
                "failure_reason": f"timeout after {per_company_timeout_sec}s",
                "ticker": ticker,
                "source_url": primary_url,
                "replay_expiry_date": "",
            }
            failure_entries.append(f"{ticker}, {primary_url}, timeout after {per_company_timeout_sec}s")
            print(f"{ticker:<6} | timeout                    | N/A          | {domain_for_log}")

        except Exception as e:
            err_msg = str(e)[:100]
            started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            manifest_by_ticker[ticker] = {
                "event_id": ev["id"],
                "capture_mode": "direct_media_url",
                "started_at": started_at,
                "ended_at": started_at,
                "duration_sec": 0.0,
                "sample_rate": 0,
                "file_size": 0,
                "sha256": "",
                "failure_reason": err_msg,
                "ticker": ticker,
                "source_url": primary_url,
                "replay_expiry_date": "",
            }
            failure_entries.append(f"{ticker}, {primary_url}, {err_msg}")
            print(f"{ticker:<6} | error                      | N/A          | {domain_for_log}")

    # Write merged manifest
    with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in manifest_by_ticker.values():
            writer.writerow(r)

    # Append to failure log
    with open(failures_log, "a", encoding="utf-8") as f:
        for entry in failure_entries:
            f.write(entry + "\n")

    # Count total valid captured across all files
    total_valid = sum(
        1 for r in manifest_by_ticker.values()
        if float(r.get("duration_sec", 0.0) or 0.0) >= 1200.0 and r.get("sha256")
    )

    print("=" * 90)
    print(f"RUN SUMMARY: {newly_captured_count} new call(s) captured in this run.")
    print(f"TOTAL VALID CAPTURES IN MANIFEST: {total_valid}")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 2 Audio Capture Pipeline")
    parser.add_argument("--limit", type=int, default=7, help="Maximum new captures before stopping")
    parser.add_argument("--timeout", type=int, default=180, help="Per-company hard timeout in seconds")
    args = parser.parse_args()
    run_phase2_capture(target_limit=args.limit, per_company_timeout_sec=args.timeout)
