import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logger import setup_logger
from src.capture.audio_standardizer import convert_to_standard_wav

logger = setup_logger("stream_downloader")


def download_stream(
    stream_url: str,
    output_wav_path: str,
    capture_mode: str = "direct_media_url",
    timeout_sec: int = 120,
) -> Dict[str, Any]:
    """Downloads an audio stream or replay media file and normalizes it to standard 16kHz mono WAV.
    
    Supports HLS (.m3u8), progressive MP3/MP4, and direct audio webcasts.
    """
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    output_dir = Path(output_wav_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    temp_input_path = str(output_dir / f"temp_{Path(output_wav_path).name}")

    cmd = [
        "ffmpeg",
        "-y",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "5",
        "-i", stream_url,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        "-t", str(timeout_sec),  # Limit capture window for safety
        output_wav_path,
    ]

    try:
        logger.info(f"Initiating stream capture: {stream_url} via {capture_mode}...")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec + 30,
            check=True,
        )
        ended_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Inspect resulting file
        stats = convert_to_standard_wav(output_wav_path, output_wav_path)
        stats["capture_mode"] = capture_mode
        stats["started_at"] = started_at
        stats["ended_at"] = ended_at
        stats["failure_reason"] = ""
        return stats

    except subprocess.TimeoutExpired:
        logger.warning(f"Stream capture timed out after {timeout_sec}s for {stream_url}")
        return {
            "file_path": output_wav_path,
            "duration_sec": 0.0,
            "sample_rate": 0,
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
            "file_size": 0,
            "sha256": "",
            "capture_mode": capture_mode,
            "started_at": started_at,
            "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "failure_reason": str(e),
        }
