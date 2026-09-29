import os
import math
import time
import wave
import numpy as np
import soundfile as sf
import sys
import psutil
import torch
from typing import List, Dict, Any, Optional, Tuple
from faster_whisper import WhisperModel
from src.utils.logger import setup_logger
from src.transcription.vad_chunker import split_audio_into_overlapping_chunks

logger = setup_logger("asr_engine")

_MODEL_CACHE: Dict[str, WhisperModel] = {}

HALLUCINATION_PHRASES = [
    "thanks for watching",
    "thank you for watching",
    "please subscribe",
    "like and subscribe",
    "subscribe to our channel",
    "subtitles by",
    "translated by",
    "watching!",
]

# Ensure Windows site-packages CUDA DLLs (cublas, cudnn) are discoverable
if sys.platform == "win32":
    venv_site = os.path.join(sys.prefix, "Lib", "site-packages")
    for sub in ["nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_runtime/bin"]:
        p = os.path.join(venv_site, *sub.split("/"))
        if os.path.exists(p):
            try:
                os.add_dll_directory(p)
            except Exception:
                pass
            if p not in os.environ.get("PATH", ""):
                os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")


def get_worker_threads() -> int:
    """Calculates CPU worker threads based on physical cores."""
    try:
        physical_cores = psutil.cpu_count(logical=False)
        if physical_cores:
            return physical_cores
    except Exception:
        pass
    cores = os.cpu_count() or 4
    return max(1, cores // 2 if cores > 4 else cores)


def get_whisper_model(
    model_size: str = "small.en",
    compute_type: Optional[str] = None,
    device: Optional[str] = None
) -> WhisperModel:
    """Loads and caches faster-whisper CTranslate2 model instance on GPU if available, else CPU."""
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"

    threads = get_worker_threads() if device == "cpu" else 4
    key = f"{model_size}_{device}_{compute_type}_{threads}"

    if key not in _MODEL_CACHE:
        logger.info(f"Loading faster-whisper '{model_size}' on {device.upper()} (compute_type={compute_type}, cpu_threads={threads})...")
        if device == "cuda":
            _MODEL_CACHE[key] = WhisperModel(
                model_size,
                device="cuda",
                compute_type=compute_type,
                device_index=0
            )
        else:
            _MODEL_CACHE[key] = WhisperModel(
                model_size,
                device="cpu",
                compute_type=compute_type,
                cpu_threads=threads
            )
    return _MODEL_CACHE[key]


def check_hallucination(text: str, avg_logprob: float, no_speech_prob: float) -> Tuple[bool, Optional[str]]:
    """Detects Whisper hallucinations, music artifacts, or very low-confidence noise and returns rule."""
    clean = text.lower().strip()
    # 1. Drop known hallucination phrases
    for phrase in HALLUCINATION_PHRASES:
        if phrase in clean:
            if len(clean.split()) <= 6 or avg_logprob < -0.4:
                return True, f"phrase ('{phrase}')"
    # 2. Drop segments that are silence/noise (high no_speech_prob AND low speech logprob)
    if no_speech_prob > 0.6 and avg_logprob < -0.6:
        return True, f"no_speech_prob ({no_speech_prob:.2f} > 0.6) & avg_logprob ({avg_logprob:.2f} < -0.6)"
    # 3. Drop severely degenerate speech
    if avg_logprob < -1.2:
        return True, f"avg_logprob ({avg_logprob:.2f} < -1.2)"
    return False, None


def is_hallucination(text: str, avg_logprob: float, no_speech_prob: float) -> bool:
    """Detects Whisper hallucinations, music artifacts, or very low-confidence noise."""
    is_h, _ = check_hallucination(text, avg_logprob, no_speech_prob)
    return is_h


def join_words_clean(words_list: List[Dict[str, Any]]) -> str:
    """Joins words into clean text preserving punctuation attachments."""
    out = ""
    for w in words_list:
        wt = w["word"].strip()
        if not wt:
            continue
        if not out or wt in [",", ".", "!", "?", ":", ";", "%", "...", "…"] or wt.startswith((",", ".", "!", "?", ":", ";", "%")):
            out += wt
        else:
            out += " " + wt
    return out.strip()


def transcribe_live_stream_chunks(
    wav_path: str,
    max_duration_sec: Optional[float] = None,
    language: str = "en",
    initial_prompt: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float]:
    """Simulates live-call streaming ASR with word-level boundary stitching & hallucination filter:
    
    1. Splits WAV into 60s windows with 3s overlap.
    2. Feeds chunks sequentially (beam_size=1, condition_on_prev=False, initial_prompt=None).
    3. Safety re-pass: fills internal gaps > 5s or ellipsis truncation slices inside gap windows.
    4. Exact word-level boundary stitching: for chunk k starting at S_k, B = S_k + 1.5s.
    5. Hallucination filter: drops no_speech_prob > 0.6, avg_logprob < -1.0, or music artifacts.
    6. Measures REAL processing time per chunk including safety re-pass.
    
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
    model = get_whisper_model(model_size=model_name)

    chunks = split_audio_into_overlapping_chunks(
        wav_path,
        chunk_len_sec=60.0,
        overlap_sec=3.0,
        max_duration_sec=total_duration
    )

    all_words = []
    chunk_metrics = []
    dropped_hallucinations = 0

    for k, ch in enumerate(chunks):
        start_sample = int(ch["start_sec"] * sample_rate)
        end_sample = int(ch["end_sec"] * sample_rate)
        chunk_audio = data[start_sample:end_sample]

        # Overlap boundary rule: B = S_k + 1.5s
        b_left = (ch["start_sec"] + 1.5) if k > 0 else 0.0
        b_right = (chunks[k+1]["start_sec"] + 1.5) if (k + 1 < len(chunks)) else total_duration

        t0 = time.perf_counter()

        # Primary pass
        segments, info = model.transcribe(
            chunk_audio,
            beam_size=1,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=None,
            language=language if language != "en" else "en"
        )

        chunk_segs = list(segments)
        refined_segs = []

        # Filter hallucinations on chunk segments
        valid_chunk_segs = []
        chunk_dropped_segs = []
        for seg in chunk_segs:
            no_speech = getattr(seg, "no_speech_prob", 0.0)
            is_h, rule = check_hallucination(seg.text, seg.avg_logprob, no_speech)
            if is_h:
                dropped_hallucinations += 1
                chunk_dropped_segs.append({
                    "text": seg.text.strip(),
                    "start": round(ch["start_sec"] + seg.start, 2),
                    "end": round(ch["start_sec"] + seg.end, 2),
                    "rule": rule,
                    "avg_logprob": round(seg.avg_logprob, 3),
                    "no_speech_prob": round(no_speech, 3)
                })
                continue
            valid_chunk_segs.append(seg)

        # Safety re-pass detection
        for i, seg in enumerate(valid_chunk_segs):
            refined_segs.append((seg, None))
            next_start = valid_chunk_segs[i+1].start if (i + 1 < len(valid_chunk_segs)) else ch["duration_sec"]
            gap_dur = next_start - seg.end
            ends_with_ellipsis = seg.text.strip().endswith("...") or seg.text.strip().endswith("…")

            if (gap_dur > 5.0 and next_start - seg.end > 5.0) or (ends_with_ellipsis and gap_dur > 2.0):
                w_start = max(0.0, seg.end)
                w_end = min(ch["duration_sec"], next_start)
                if w_end - w_start >= 3.0:
                    w_start_samp = int(w_start * sample_rate)
                    w_end_samp = int(w_end * sample_rate)
                    gap_audio = chunk_audio[w_start_samp:w_end_samp]
                    if len(gap_audio) > int(1.0 * sample_rate):
                        repass_segs, _ = model.transcribe(
                            gap_audio,
                            beam_size=5,
                            word_timestamps=True,
                            vad_filter=False,
                            condition_on_previous_text=False,
                            initial_prompt=None,
                            language=language if language != "en" else "en"
                        )
                        for r_seg in repass_segs:
                            no_sp = getattr(r_seg, "no_speech_prob", 0.0)
                            is_h_r, rule_r = check_hallucination(r_seg.text, r_seg.avg_logprob, no_sp)
                            if not is_h_r:
                                refined_segs.append((r_seg, w_start))
                            else:
                                chunk_dropped_segs.append({
                                    "text": r_seg.text.strip(),
                                    "start": round(ch["start_sec"] + w_start + r_seg.start, 2),
                                    "end": round(ch["start_sec"] + w_start + r_seg.end, 2),
                                    "rule": rule_r,
                                    "avg_logprob": round(r_seg.avg_logprob, 3),
                                    "no_speech_prob": round(no_sp, 3)
                                })

        # Check start gap
        if valid_chunk_segs and valid_chunk_segs[0].start > 5.0:
            w_end = valid_chunk_segs[0].start
            w_end_samp = int(w_end * sample_rate)
            gap_audio = chunk_audio[:w_end_samp]
            if len(gap_audio) > int(2.0 * sample_rate):
                repass_segs, _ = model.transcribe(
                    gap_audio,
                    beam_size=5,
                    word_timestamps=True,
                    vad_filter=False,
                    condition_on_previous_text=False,
                    initial_prompt=None,
                    language=language if language != "en" else "en"
                )
                for r_seg in repass_segs:
                    no_sp = getattr(r_seg, "no_speech_prob", 0.0)
                    is_h_r, rule_r = check_hallucination(r_seg.text, r_seg.avg_logprob, no_sp)
                    if not is_h_r:
                        refined_segs.insert(0, (r_seg, 0.0))
                    else:
                        chunk_dropped_segs.append({
                            "text": r_seg.text.strip(),
                            "start": round(ch["start_sec"] + r_seg.start, 2),
                            "end": round(ch["start_sec"] + r_seg.end, 2),
                            "rule": rule_r,
                            "avg_logprob": round(r_seg.avg_logprob, 3),
                            "no_speech_prob": round(no_sp, 3)
                        })

        # Extract words with boundary filtering
        for seg_item, offset in refined_segs:
            base_offset = ch["start_sec"] + (offset if offset is not None else 0.0)

            if seg_item.words:
                for w in seg_item.words:
                    g_w_start = round(base_offset + w.start, 3)
                    g_w_end = round(base_offset + w.end, 3)
                    w_text = w.word.strip()
                    if not w_text:
                        continue
                    if offset is not None:
                        all_words.append({
                            "start": g_w_start,
                            "end": g_w_end,
                            "word": w_text,
                            "prob": w.probability
                        })
                    elif b_left <= g_w_start < b_right:
                        all_words.append({
                            "start": g_w_start,
                            "end": g_w_end,
                            "word": w_text,
                            "prob": w.probability
                        })
            else:
                g_seg_start = round(base_offset + seg_item.start, 3)
                g_seg_end = round(base_offset + seg_item.end, 3)
                if (offset is not None) or (b_left <= g_seg_start < b_right):
                    words = seg_item.text.strip().split()
                    if words:
                        dur_per_word = (g_seg_end - g_seg_start) / len(words)
                        for wi, w_str in enumerate(words):
                            all_words.append({
                                "start": round(g_seg_start + wi * dur_per_word, 3),
                                "end": round(g_seg_start + (wi + 1) * dur_per_word, 3),
                                "word": w_str,
                                "prob": min(1.0, math.exp(seg_item.avg_logprob))
                            })

        t_proc = round(time.perf_counter() - t0, 3)
        chunk_metrics.append({
            "chunk_idx": ch["chunk_idx"],
            "start_sec": ch["start_sec"],
            "end_sec": ch["end_sec"],
            "duration_sec": ch["duration_sec"],
            "proc_time_sec": t_proc,
            "rtf": round(t_proc / max(0.001, ch["duration_sec"]), 4),
            "dropped_segments": chunk_dropped_segs,
        })

    # Sort words chronologically
    all_words.sort(key=lambda w: w["start"])

    # Group into clean segments (pause > 1.2s or end of sentence or max 25 words)
    stitched_segments = []
    if all_words:
        curr_words = [all_words[0]]
        for w in all_words[1:]:
            prev_w = curr_words[-1]
            pause = w["start"] - prev_w["end"]
            prev_ends_sentence = prev_w["word"].strip().endswith((".", "!", "?"))
            if pause > 1.2 or (prev_ends_sentence and pause > 0.3) or len(curr_words) >= 25:
                seg_text = join_words_clean(curr_words)
                seg_conf = round(sum(cw["prob"] for cw in curr_words) / len(curr_words), 3)
                stitched_segments.append({
                    "start": round(curr_words[0]["start"], 2),
                    "end": round(curr_words[-1]["end"], 2),
                    "text": seg_text,
                    "confidence": seg_conf
                })
                curr_words = [w]
            else:
                curr_words.append(w)

        if curr_words:
            seg_text = join_words_clean(curr_words)
            seg_conf = round(sum(cw["prob"] for cw in curr_words) / len(curr_words), 3)
            stitched_segments.append({
                "start": round(curr_words[0]["start"], 2),
                "end": round(curr_words[-1]["end"], 2),
                "text": seg_text,
                "confidence": seg_conf
            })

    if dropped_hallucinations > 0:
        logger.info(f"Dropped {dropped_hallucinations} hallucination/low-confidence segments from {os.path.basename(wav_path)}")

    return stitched_segments, chunk_metrics, total_duration
