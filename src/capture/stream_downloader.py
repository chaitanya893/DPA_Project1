import os
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import setup_logger
from src.capture.audio_standardizer import convert_to_standard_wav, compute_sha256, get_wav_properties

logger = setup_logger("stream_downloader")

# Rate limiter tracking domain last request time
_LAST_REQUEST_TIME_BY_DOMAIN: Dict[str, float] = {}
RATE_LIMIT_DELAY_SEC = 2.5
USER_AGENT = "EarningsCallCaptureBot/1.0 (Contact: chaitanya@example.com)"


def _enforce_rate_limit(url: str) -> None:
    """Enforces 2.5s domain rate limit."""
    try:
        domain = urllib.parse.urlparse(url).netloc.lower()
        if domain in _LAST_REQUEST_TIME_BY_DOMAIN:
            elapsed = time.time() - _LAST_REQUEST_TIME_BY_DOMAIN[domain]
            if elapsed < RATE_LIMIT_DELAY_SEC:
                time.sleep(RATE_LIMIT_DELAY_SEC - elapsed)
        _LAST_REQUEST_TIME_BY_DOMAIN[domain] = time.time()
    except Exception:
        pass


def download_stream(
    stream_url: str,
    output_wav_path: str,
    capture_mode: str = "direct_media_url",
    timeout_sec: int = 1800,
    max_duration_sec: Optional[int] = None,
) -> Dict[str, Any]:
    """Downloads an audio stream or replay media file and normalizes it to standard 16kHz mono WAV.
    
    Supports direct streams (HLS/m3u8/mp3/mp4/m4a/aac) and public webcast replays via FFmpeg.
    Strictly rejects YouTube URLs per compliance policy.
    """
    # Strict compliance check
    url_l = stream_url.lower()
    if "youtube.com" in url_l or "youtu.be" in url_l:
        raise ValueError(f"Prohibited source domain: YouTube is forbidden by compliance rules. URL: {stream_url}")

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    output_dir = Path(output_wav_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    _enforce_rate_limit(stream_url)

    try:
        logger.info(f"Initiating stream capture: {stream_url} via {capture_mode}...")

        # Direct HTTP / HLS stream capture via ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-user_agent", USER_AGENT,
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", stream_url,
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
        ]
        if max_duration_sec:
            cmd.extend(["-t", str(max_duration_sec)])
        cmd.append(output_wav_path)

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_sec)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg failed (code {res.returncode}): {res.stderr.decode('utf-8', errors='ignore')[:300]}")

        ended_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Inspect resulting file
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
            "capture_mode": capture_mode,
            "started_at": started_at,
            "ended_at": ended_at,
            "failure_reason": "",
        }

    except subprocess.TimeoutExpired:
        logger.warning(f"Stream capture timed out after {timeout_sec}s for {stream_url}")
        return {
            "file_path": output_wav_path,
            "duration_sec": 0.0,
            "sample_rate": 0,
            "channels": 0,
            "bit_depth": 0,
            "file_size": 0,
            "sha256": "",
            "capture_mode": capture_mode,
            "started_at": started_at,
            "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "failure_reason": f"Capture timed out after {timeout_sec}s",
        }
    except Exception as e:
        logger.error(f"Stream capture failed for {stream_url}: {e}")
        return {
            "file_path": output_wav_path,
            "duration_sec": 0.0,
            "sample_rate": 0,
            "channels": 0,
            "bit_depth": 0,
            "file_size": 0,
            "sha256": "",
            "capture_mode": capture_mode,
            "started_at": started_at,
            "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "failure_reason": str(e),
        }
