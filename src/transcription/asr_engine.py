import os
import math
import time
import wave
import numpy as np
import soundfile as sf
from typing import List, Dict, Any, Optional, Tuple
from faster_whisper import WhisperModel
from src.utils.logger import setup_logger
from src.transcription.vad_chunker import split_audio_into_overlapping_chunks, deduplicate_overlap_words

logger = setup_logger("asr_engine")

_MODEL_CACHE: Dict[str, WhisperModel] = {}


def get_worker_threads() -> int:
    """Calculates CPU worker threads: cores - 2 (minimum 1)."""
    cores = os.cpu_count() or 4
    return max(1, cores - 2)


def get_whisper_model(model_size: str = "small.en", compute_type: str = "int8") -> WhisperModel:
    """Loads and caches the faster-whisper CTranslate2 model instance."""
    threads = get_worker_threads()
    key = f"{model_size}_{compute_type}_{threads}"
    if key not in _MODEL_CACHE:
        logger.info(f"Loading faster-whisper '{model_size}' on CPU (compute_type={compute_type}, cpu_threads={threads})...")
        _MODEL_CACHE[key] = WhisperModel(
            model_size,
            device="cpu",
            compute_type=compute_type,
            cpu_threads=threads
        )
    return _MODEL_CACHE[key]


def transcribe_live_stream_chunks(
    wav_path: str,
    max_duration_sec: Optional[float] = None,
    language: str = "en"
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]:
    """Simulates live-call streaming ASR:
    
    1. Splits WAV into 60s windows with 3s overlap.
    2. Feeds chunks sequentially through ASR engine.
    3. Measures the REAL processing time of every individual chunk.
    4. Stitches and deduplicates overlapping boundaries.
    
    Returns (stitched_segments, chunk_metrics, total_audio_duration).
    """
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"Audio file not found: {wav_path}")

    # Read audio data
    data, sample_rate = sf.read(wav_path, dtype='float32')
    if data.ndim > 1:
        data = data.mean(axis=1)

    total_duration = len(data) / float(sample_rate)
    if max_duration_sec:
        total_duration = min(total_duration, max_duration_sec)
        data = data[:int(total_duration * sample_rate)]

    model_name = "small.en" if language == "en" else "small"
    model = get_whisper_model(model_size=model_name, compute_type="int8")

    chunks = split_audio_into_overlapping_chunks(
        wav_path,
        chunk_len_sec=60.0,
        overlap_sec=3.0,
        max_duration_sec=total_duration
    )

    all_raw_segments = []
    chunk_metrics = []
    prev_chunk_text = ""

    for ch in chunks:
        start_sample = int(ch["start_sec"] * sample_rate)
        end_sample = int(ch["end_sec"] * sample_rate)
        chunk_audio = data[start_sample:end_sample]

        # Measure REAL processing time of this chunk
        t0 = time.perf_counter()
        segments, info = model.transcribe(
            chunk_audio,
            beam_size=1,
            word_timestamps=True,
            vad_filter=True,
            language=language if language != "en" else "en"
        )

        chunk_segs = list(segments)
        t_proc = round(time.perf_counter() - t0, 3)

        chunk_metrics.append({
            "chunk_idx": ch["chunk_idx"],
            "start_sec": ch["start_sec"],
            "end_sec": ch["end_sec"],
            "duration_sec": ch["duration_sec"],
            "proc_time_sec": t_proc,
            "rtf": round(t_proc / max(0.001, ch["duration_sec"]), 4),
            "num_segments": len(chunk_segs)
        })

        # Process segments with global timestamp offset
        chunk_full_text = ""
        for seg in chunk_segs:
            text = seg.text.strip()
            if not text:
                continue

            # Confidence = exp(avg_logprob)
            conf = round(min(1.0, max(0.0, math.exp(seg.avg_logprob))), 3)

            global_start = round(ch["start_sec"] + seg.start, 2)
            global_end = round(min(total_duration, ch["start_sec"] + seg.end), 2)

            all_raw_segments.append({
                "chunk_idx": ch["chunk_idx"],
                "start": global_start,
                "end": global_end,
                "text": text,
                "confidence": conf
            })
            chunk_full_text += " " + text

    # Stitch and deduplicate overlap across chunks
    stitched_segments = []
    prev_text = ""
    for seg in all_raw_segments:
        clean_text = deduplicate_overlap_words(prev_text, seg["text"])
        if clean_text:
            stitched_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": clean_text,
                "confidence": seg["confidence"]
            })
            prev_text = clean_text

    return stitched_segments, chunk_metrics, total_duration
