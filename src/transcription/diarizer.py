import os
import time
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
import torch
import soundfile as sf
import psutil
from dotenv import load_dotenv
from pyannote.audio import Pipeline
from src.utils.logger import setup_logger

logger = setup_logger("diarizer")

_DIARIZATION_PIPELINE = None


def get_physical_cores() -> int:
    """Returns the number of physical CPU cores."""
    try:
        physical_cores = psutil.cpu_count(logical=False)
        if physical_cores:
            return physical_cores
    except Exception:
        pass
    cores = os.cpu_count() or 4
    return max(1, cores // 2 if cores > 4 else cores)


def get_diarization_pipeline() -> Pipeline:
    """Loads and caches pyannote/speaker-diarization-3.1 using HF_TOKEN from .env.
    
    If loading fails, raises RuntimeError immediately – no fallback heuristic.
    Places model on CUDA if available, verifying real device placement.
    """
    global _DIARIZATION_PIPELINE
    if _DIARIZATION_PIPELINE is None:
        load_dotenv()
        token = os.getenv("HF_TOKEN")
        if not token:
            raise RuntimeError(
                "HF_TOKEN is missing or empty in .env. "
                "Pyannote requires a HuggingFace authentication token with accepted conditions for "
                "pyannote/speaker-diarization-3.1, pyannote/segmentation-3.0, and pyannote/speaker-diarization-community-1."
            )

        cuda_available = torch.cuda.is_available()
        device = torch.device("cuda" if cuda_available else "cpu")

        if not cuda_available:
            num_threads = get_physical_cores()
            torch.set_num_threads(num_threads)
            logger.info(f"Set PyTorch CPU threads to {num_threads} (physical cores) for pyannote diarization.")

        logger.info("Initializing pyannote/speaker-diarization-3.1 pipeline...")
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=token
            )
            pipeline.to(device)

            # Strict device verification
            if cuda_available:
                # Check underlying model device
                seg_device = getattr(getattr(pipeline, "_segmentation", None), "model", None)
                if seg_device is not None:
                    actual_dev = next(seg_device.parameters()).device
                    if actual_dev.type != "cuda":
                        raise RuntimeError(f"Pyannote segmentation model is on {actual_dev} instead of CUDA!")
                logger.info(f"pyannote/speaker-diarization-3.1 initialized successfully on CUDA ({torch.cuda.get_device_name(0)}).")
            else:
                logger.info("pyannote/speaker-diarization-3.1 initialized successfully on CPU.")

            _DIARIZATION_PIPELINE = pipeline
        except Exception as e:
            logger.error(f"Failed to load pyannote/speaker-diarization-3.1: {e}")
            raise RuntimeError(f"Pyannote diarization failed to load: {e}") from e

    return _DIARIZATION_PIPELINE


def diarize_audio(
    audio_input: Union[str, np.ndarray],
    sample_rate: int = 16000,
    max_duration_sec: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Runs pyannote/speaker-diarization-3.1 on audio file or in-memory array.
    
    Returns list of dicts: [{'start': float, 'end': float, 'speaker_id': str}]
    """
    pipeline = get_diarization_pipeline()
    cuda_available = torch.cuda.is_available()
    
    if isinstance(audio_input, np.ndarray):
        if audio_input.ndim > 1:
            audio_input = audio_input.mean(axis=1)
        if max_duration_sec:
            audio_input = audio_input[:int(max_duration_sec * sample_rate)]
        
        waveform = torch.from_numpy(audio_input).unsqueeze(0).float()
        pipeline_input = {"waveform": waveform, "sample_rate": sample_rate}
        dur_sec = len(audio_input) / float(sample_rate)
    else:
        data, sr = sf.read(audio_input, dtype='float32')
        if data.ndim > 1:
            data = data.mean(axis=1)
        if max_duration_sec:
            data = data[:int(max_duration_sec * sr)]
        waveform = torch.from_numpy(data).unsqueeze(0).float()
        pipeline_input = {"waveform": waveform, "sample_rate": sr}
        dur_sec = len(data) / float(sr)

    if cuda_available:
        logger.info(f"Running pyannote diarization on CUDA ({dur_sec:.1f}s audio)...")
    else:
        num_threads = get_physical_cores()
        logger.info(f"Running pyannote diarization on CPU ({dur_sec:.1f}s audio, {num_threads} threads)...")

    diarization_output = pipeline(pipeline_input)
    
    diar_segments = []
    for turn, _, speaker in diarization_output.itertracks(yield_label=True):
        if max_duration_sec and turn.start >= max_duration_sec:
            continue
        end = min(turn.end, max_duration_sec) if max_duration_sec else turn.end
        diar_segments.append({
            "start": round(turn.start, 2),
            "end": round(end, 2),
            "speaker_id": str(speaker)
        })
        
    if cuda_available:
        mem_mb = torch.cuda.memory_allocated() / (1024**2)
        logger.info(f"Pyannote diarization completed on CUDA: {len(diar_segments)} speaker turns detected (VRAM: {mem_mb:.1f} MB).")
    else:
        logger.info(f"Pyannote diarization completed on CPU: {len(diar_segments)} speaker turns detected.")
    return diar_segments


def align_asr_segments_with_diarization(
    asr_segments: List[Dict[str, Any]],
    diar_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Assigns each ASR segment the speaker ID with maximum temporal overlap."""
    if not diar_segments:
        for seg in asr_segments:
            seg["speaker_id"] = "UNDIARIZED"
        return asr_segments

    for seg in asr_segments:
        s_start = seg["start"]
        s_end = seg["end"]
        best_speaker = None
        max_overlap = -1.0

        for d in diar_segments:
            d_start = d["start"]
            d_end = d["end"]

            overlap = max(0.0, min(s_end, d_end) - max(s_start, d_start))
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = d["speaker_id"]

        seg["speaker_id"] = best_speaker or "SPEAKER_00"

    return asr_segments
