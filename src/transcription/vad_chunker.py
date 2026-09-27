import os
import math
import wave
import time
from typing import List, Dict, Any, Tuple
import numpy as np
import soundfile as sf
import torch

_SILERO_MODEL = None
_SILERO_UTILS = None


def get_silero_vad_model():
    """Loads and caches the official Silero VAD model."""
    global _SILERO_MODEL, _SILERO_UTILS
    if _SILERO_MODEL is None:
        model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False,
            trust_repo=True
        )
        _SILERO_MODEL = model
        _SILERO_UTILS = utils
    return _SILERO_MODEL, _SILERO_UTILS


def split_audio_into_overlapping_chunks(
    wav_path: str,
    chunk_len_sec: float = 60.0,
    overlap_sec: float = 3.0,
    max_duration_sec: float = None
) -> List[Dict[str, Any]]:
    """Splits a WAV file into 60s windows with 3s overlap for live-call streaming simulation.
    
    Windows: [0, 60], [57, 117], [114, 174], ...
    Returns chunk descriptors with exact sample boundaries.
    """
    with wave.open(wav_path, 'rb') as wf:
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        total_duration = n_frames / float(sample_rate)

    if max_duration_sec:
        total_duration = min(total_duration, max_duration_sec)

    step_sec = chunk_len_sec - overlap_sec
    chunks = []
    chunk_idx = 0
    start_sec = 0.0

    while start_sec < total_duration:
        end_sec = min(start_sec + chunk_len_sec, total_duration)
        duration = end_sec - start_sec

        chunks.append({
            "chunk_idx": chunk_idx,
            "start_sec": round(start_sec, 3),
            "end_sec": round(end_sec, 3),
            "duration_sec": round(duration, 3),
            "is_final": (end_sec >= total_duration)
        })

        if end_sec >= total_duration:
            break

        start_sec += step_sec
        chunk_idx += 1

    return chunks


def apply_vad_filter(audio_array: np.ndarray, sample_rate: int = 16000) -> List[Dict[str, float]]:
    """Applies Silero VAD to detect speech timestamps within an audio segment."""
    try:
        model, utils = get_silero_vad_model()
        (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils

        tensor_audio = torch.from_numpy(audio_array).float()
        if tensor_audio.ndim > 1:
            tensor_audio = tensor_audio.mean(dim=-1)

        speech_timestamps = get_speech_timestamps(
            tensor_audio,
            model,
            sampling_rate=sample_rate,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=100
        )
        return speech_timestamps
    except Exception as e:
        # Fallback to full segment if VAD hub load is unavailable
        return [{"start": 0, "end": len(audio_array)}]


def deduplicate_overlap_words(prev_text: str, current_text: str) -> str:
    """Stitches consecutive chunk transcripts by removing duplicate words in the 3s overlap window."""
    if not prev_text or not current_text:
        return current_text.strip()

    prev_words = prev_text.strip().split()
    curr_words = current_text.strip().split()

    if not prev_words or not curr_words:
        return current_text.strip()

    # Search for overlapping word suffixes/prefixes up to 15 words
    max_k = min(15, len(prev_words), len(curr_words))
    best_overlap = 0

    prev_clean = [w.lower().strip(".,!?:;\"'") for w in prev_words]
    curr_clean = [w.lower().strip(".,!?:;\"'") for w in curr_words]

    for k in range(max_k, 0, -1):
        if prev_clean[-k:] == curr_clean[:k]:
            best_overlap = k
            break

    if best_overlap > 0:
        return " ".join(curr_words[best_overlap:]).strip()

    return current_text.strip()
