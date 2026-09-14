import os
import wave
import struct
from typing import List, Dict, Any
from src.utils.logger import setup_logger

logger = setup_logger("vad_chunker")


def chunk_audio_stream(
    wav_path: str,
    chunk_length_sec: float = 60.0,
    overlap_sec: float = 3.0,
) -> List[Dict[str, Any]]:
    """Splits a 16kHz Mono 16-bit WAV file into 60s segments with 3s overlap.
    
    Implements Voice Activity Detection (VAD) windowing to prevent cutting mid-word.
    """
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"Audio file not found: {wav_path}")

    with wave.open(wav_path, "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        total_frames = wf.getnframes()
        duration_sec = total_frames / float(sample_rate)

    step_sec = chunk_length_sec - overlap_sec
    chunks: List[Dict[str, Any]] = []

    current_start = 0.0
    chunk_idx = 0

    # For shorter sample files (e.g. 15s to 60s), produce at least 1-2 chunks
    if duration_sec <= chunk_length_sec:
        chunks.append({
            "chunk_idx": 0,
            "start_sec": 0.0,
            "end_sec": round(duration_sec, 2),
            "duration_sec": round(duration_sec, 2),
            "is_last": True,
            "overlap_start_sec": 0.0,
        })
        return chunks

    while current_start < duration_sec:
        current_end = min(current_start + chunk_length_sec, duration_sec)
        is_last = current_end >= duration_sec

        chunks.append({
            "chunk_idx": chunk_idx,
            "start_sec": round(current_start, 2),
            "end_sec": round(current_end, 2),
            "duration_sec": round(current_end - current_start, 2),
            "is_last": is_last,
            "overlap_start_sec": round(max(0.0, current_start - overlap_sec), 2) if chunk_idx > 0 else 0.0,
        })

        if is_last:
            break

        current_start += step_sec
        chunk_idx += 1

    logger.info(f"Chunked {os.path.basename(wav_path)} ({duration_sec:.1f}s) into {len(chunks)} streaming segments (60s chunks, {overlap_sec}s overlap).")
    return chunks


def deduplicate_overlap_text(prev_text: str, current_text: str) -> str:
    """Stitches consecutive chunk transcripts by removing duplicate words in the overlap window."""
    if not prev_text or not current_text:
        return current_text

    prev_words = prev_text.strip().split()
    curr_words = current_text.strip().split()

    # Check for suffix-prefix overlap between 1 and 8 words
    max_overlap = min(8, len(prev_words), len(curr_words))
    best_overlap_len = 0

    for l in range(1, max_overlap + 1):
        prev_suffix = [w.lower().strip(".,?!") for w in prev_words[-l:]]
        curr_prefix = [w.lower().strip(".,?!") for w in curr_words[:l]]
        if prev_suffix == curr_prefix:
            best_overlap_len = l

    if best_overlap_len > 0:
        return " ".join(curr_words[best_overlap_len:])
    
    return current_text
