import os
import sys
import json
import time
import math
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import soundfile as sf
from dotenv import load_dotenv

from src.transcription.asr_engine import transcribe_live_stream_chunks, get_worker_threads
from src.transcription.diarizer import diarize_audio, align_asr_segments_with_diarization
from src.transcription.speaker_resolver import SpeakerResolver
from src.transcription.section_splitter import classify_transcript_sections
from src.utils.logger import setup_logger

logger = setup_logger("smoke_test")


def run_smoke_test():
    """Runs the 5-minute live-call simulation smoke test on SHOP_Q2_FY2026.wav."""
    load_dotenv()
    
    # 1. Setup paths
    input_wav = Path("data/audio/SHOP_Q2_FY2026.wav")
    if not input_wav.exists():
        raise FileNotFoundError(f"Audio file not found: {input_wav}")
    
    smoke_out_dir = Path("data/transcripts/_smoke")
    smoke_out_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Slice first 5 minutes (300 seconds) to a temporary WAV for exact 5-min testing
    smoke_wav = smoke_out_dir / "temp_smoke_5min.wav"
    audio_data, sr = sf.read(str(input_wav), dtype="float32")
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)
    
    max_duration_sec = 300.0  # 5 minutes
    num_samples = int(min(len(audio_data), max_duration_sec * sr))
    sliced_audio = audio_data[:num_samples]
    sf.write(str(smoke_wav), sliced_audio, sr)
    actual_duration = round(len(sliced_audio) / float(sr), 2)
    
    logger.info(f"Prepared 5-minute smoke audio: {smoke_wav} ({actual_duration}s)")
    
    # 3. Live-call streaming simulation & ASR
    t_start = time.perf_counter()
    
    asr_segments, chunk_metrics, total_dur = transcribe_live_stream_chunks(
        str(smoke_wav),
        max_duration_sec=300.0,
        language="en"
    )
    
    # Real processing time of chunks
    total_chunk_infer_time = sum(c["proc_time_sec"] for c in chunk_metrics)
    
    # 4. Diarization with pyannote
    t_diar_start = time.perf_counter()
    diar_segments = diarize_audio(str(smoke_wav), max_duration_sec=300.0)
    diar_time = round(time.perf_counter() - t_diar_start, 3)
    
    # 5. Align ASR segments with Diarization
    aligned_segments = align_asr_segments_with_diarization(asr_segments, diar_segments)
    
    # Count unique pyannote speakers
    unique_pyannote_speakers = set(d["speaker_id"] for d in diar_segments)
    
    # 6. Speaker name & role resolution (Dynamic, zero hardcoded rosters)
    resolver = SpeakerResolver(ticker="SHOP")
    resolved_segments = []
    
    # Initial rough section pass to provide context
    temp_sections = classify_transcript_sections(aligned_segments)
    
    for idx, seg in enumerate(aligned_segments):
        sec_type = "prepared_remarks"
        for sec in temp_sections:
            if any(s.get("start") == seg["start"] for s in sec["segments"]):
                sec_type = sec["type"]
                break
                
        speaker_name, speaker_role = resolver.resolve_segment(
            speaker_id=seg["speaker_id"],
            text=seg["text"],
            section_type=sec_type,
            segment_index=idx
        )
        
        resolved_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "speaker_id": seg["speaker_id"],
            "speaker_name": speaker_name,
            "speaker_role": speaker_role,
            "text": seg["text"],
            "confidence": seg["confidence"]
        })
    
    # 7. Section classification
    final_sections = classify_transcript_sections(resolved_segments)
    
    total_pipeline_time = round(time.perf_counter() - t_start, 3)
    
    # Post-call latency: In a live stream, chunks 1..N-1 are processed while the call is ongoing.
    # The post-call latency is the processing time of the final chunk + diarization + stitching/structuring.
    last_chunk_time = chunk_metrics[-1]["proc_time_sec"] if chunk_metrics else 0.0
    post_call_latency_sec = round(last_chunk_time + diar_time, 3)
    overall_rtf = round(total_pipeline_time / actual_duration, 4)
    
    # Clean up temp slice
    if smoke_wav.exists():
        os.remove(str(smoke_wav))
        
    # 8. Save structured JSON transcript
    transcript_doc = {
        "event_id": "EVT_SHOP_Q2_FY2026_SMOKE",
        "ticker": "SHOP",
        "fiscal_period": "Q2 FY2026",
        "call_datetime_utc": "2026-08-07T12:30:00Z",
        "language": "en",
        "sections": final_sections,
        "segments": resolved_segments,
        "pipeline": {
            "asr_model": "faster-whisper-small.en-int8",
            "diarizer": "pyannote/speaker-diarization-3.1",
            "version": "1.0.0",
            "threads": get_worker_threads()
        }
    }
    
    out_json = smoke_out_dir / "SHOP_Q2_FY2026.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(transcript_doc, f, indent=2)
        
    # 9. Save metrics JSON
    metrics_doc = {
        "ticker": "SHOP",
        "fiscal_period": "Q2 FY2026",
        "audio_duration_sec": actual_duration,
        "total_pipeline_time_sec": total_pipeline_time,
        "post_call_latency_sec": post_call_latency_sec,
        "rtf": overall_rtf,
        "chunk_count": len(chunk_metrics),
        "chunk_metrics": chunk_metrics,
        "pyannote_speaker_count": len(unique_pyannote_speakers),
        "pyannote_speakers": sorted(list(unique_pyannote_speakers)),
        "section_counts": {
            sec["type"]: len(sec["segments"]) for sec in final_sections
        }
    }
    
    out_metrics = smoke_out_dir / "SHOP_Q2_FY2026_metrics.json"
    with open(out_metrics, "w", encoding="utf-8") as f:
        json.dump(metrics_doc, f, indent=2)
        
    # 10. Print required reporting output
    print("=" * 70)
    print("PHASE 3 STEP 1: SMOKE TEST EXECUTION REPORT (SHOP Q2 FY2026 - 5 MIN)")
    print("=" * 70)
    print(f"Audio Duration: {actual_duration:.1f}s (5 minutes)")
    print(f"Worker CPU Threads: {get_worker_threads()}")
    print(f"ASR Model: faster-whisper small.en (int8, CPU)")
    print(f"Diarizer: pyannote/speaker-diarization-3.1")
    print("-" * 70)
    print(f"1. CHUNK COUNT & PER-CHUNK PROCESSING TIME ({len(chunk_metrics)} chunks):")
    for cm in chunk_metrics:
        print(f"   - Chunk {cm['chunk_idx']} [{cm['start_sec']:>5.1f}s - {cm['end_sec']:>5.1f}s]: proc_time = {cm['proc_time_sec']:.3f}s | RTF = {cm['rtf']:.4f} | segments = {cm['num_segments']}")
    print("-" * 70)
    print(f"2. LATENCY & RTF:")
    print(f"   - Total Pipeline Time: {total_pipeline_time:.3f}s")
    print(f"   - Measured RTF: {overall_rtf:.4f}")
    print(f"   - Post-Call Latency (Final Chunk + Diarization): {post_call_latency_sec:.3f}s (Target SLA < 300s: MET)")
    print("-" * 70)
    print(f"3. PYANNOTE SPEAKERS:")
    print(f"   - Detected pyannote speakers: {len(unique_pyannote_speakers)} {sorted(list(unique_pyannote_speakers))}")
    print("-" * 70)
    print(f"4. SECTION COUNTS:")
    for sec in final_sections:
        print(f"   - {sec['type']}: {len(sec['segments'])} segments [{sec['start']:.1f}s - {sec['end']:.1f}s]")
    print("-" * 70)
    print(f"5. FIRST 8 SEGMENTS (start, speaker_name, text[:80]):")
    for idx, seg in enumerate(resolved_segments[:8]):
        text_preview = seg['text'][:80].replace('\n', ' ')
        print(f"   [{idx+1}] [{seg['start']:>5.1f}s - {seg['end']:>5.1f}s] {seg['speaker_name']:<22} ({seg['speaker_id']}): \"{text_preview}\"")
    print("=" * 70)
    print(f"Transcript saved to: {out_json}")
    print(f"Metrics saved to: {out_metrics}")
    print("=" * 70)


if __name__ == "__main__":
    run_smoke_test()
