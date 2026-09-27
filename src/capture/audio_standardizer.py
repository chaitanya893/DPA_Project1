import hashlib
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Dict, Any, Tuple
from src.utils.logger import setup_logger

logger = setup_logger("audio_standardizer")


def compute_sha256(file_path: str) -> str:
    """Calculates SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_wav_properties(file_path: str) -> Tuple[float, int, int, int]:
    """Inspects a WAV file using standard wave module: returns (duration_sec, sample_rate, channels, bit_depth)."""
    with wave.open(file_path, "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sampwidth = wf.getsampwidth()
        bit_depth = sampwidth * 8
        frames = wf.getnframes()
        duration_sec = round(frames / float(sample_rate), 2)
        return duration_sec, sample_rate, channels, bit_depth


def convert_to_standard_wav(input_path: str, output_path: str) -> Dict[str, Any]:
    """Converts input audio file to standardized WAV: 16 kHz, Mono, 16-bit PCM via FFmpeg."""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(output_path),
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed for {input_path}: {res.stderr}")

    duration_sec, sample_rate, channels, bit_depth = get_wav_properties(output_path)
    file_size = os.path.getsize(output_path)
    sha256_hash = compute_sha256(output_path)

    if sample_rate != 16000:
        raise ValueError(f"Sample rate must be 16000 Hz, got {sample_rate}")
    if channels != 1:
        raise ValueError(f"Audio must be mono (1 channel), got {channels}")
    if bit_depth != 16:
        raise ValueError(f"Bit depth must be 16-bit PCM, got {bit_depth}")

    logger.info(
        f"Standardized audio verified: {output_path} | "
        f"Duration: {duration_sec}s | Rate: {sample_rate}Hz | Size: {file_size} bytes"
    )

    return {
        "file_path": output_path,
        "duration_sec": duration_sec,
        "sample_rate": sample_rate,
        "channels": channels,
        "bit_depth": bit_depth,
        "file_size": file_size,
        "sha256": sha256_hash,
    }
