import os
import time
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
from pyannote.audio import Pipeline
from src.utils.logger import setup_logger

logger = setup_logger("diarizer")

_DIARIZATION_PIPELINE = None


def get_diarization_pipeline() -> Pipeline:
    """Loads and caches pyannote/speaker-diarization-3.1 using HF_TOKEN from .env.
    
    If loading fails, raises RuntimeError immediately – no fallback heuristic.
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

        logger.info("Initializing pyannote/speaker-diarization-3.1 pipeline...")
        try:
            _DIARIZATION_PIPELINE = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=token
            )
            logger.info("pyannote/speaker-diarization-3.1 initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to load pyannote/speaker-diarization-3.1: {e}")
            raise RuntimeError(f"Pyannote diarization failed to load: {e}") from e

    return _DIARIZATION_PIPELINE


def diarize_audio(
    wav_path: str,
    max_duration_sec: float = None
) -> List[Dict[str, Any]]:
    """Runs pyannote/speaker-diarization-3.1 on audio file and returns diarization segments.
    
    Returns list of dicts: [{'start': float, 'end': float, 'speaker_id': str}]
    """
    pipeline = get_diarization_pipeline()
    
    logger.info(f"Running pyannote diarization on {os.path.basename(wav_path)}...")
    diarization_output = pipeline(wav_path)
    
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
        
    logger.info(f"Pyannote diarization completed: {len(diar_segments)} speaker turns detected.")
    return diar_segments


def align_asr_segments_with_diarization(
    asr_segments: List[Dict[str, Any]],
    diar_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Assigns each ASR segment the speaker ID with maximum temporal overlap."""
    if not diar_segments:
        # Fallback speaker ID if no diarization tracks found
        for seg in asr_segments:
            seg["speaker_id"] = "SPEAKER_00"
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
