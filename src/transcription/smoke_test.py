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
import torch
from dotenv import load_dotenv

from src.transcription.asr_engine import transcribe_live_stream_chunks, get_worker_threads
from src.transcription.diarizer import diarize_audio, align_asr_segments_with_diarization
from src.transcription.speaker_resolver import SpeakerResolver
from src.transcription.section_splitter import classify_transcript_sections
from src.utils.logger import setup_logger

logger = setup_logger("smoke_test")


def run_smoke_test():
    """Runs the optimized 5-minute live-call simulation smoke test on SHOP_Q2_FY2026.wav."""
    load_dotenv()
    
    # 1. Setup paths
    input_wav = Path("data/audio/SHOP_Q2_FY2026.wav")
    if not input_wav.exists():
        raise FileNotFoundError(f"Audio file not found: {input_wav}")
    
    smoke_out_dir = Path("data/transcripts/_smoke")
    smoke_out_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Load audio once in memory (300 seconds slice)
    data, sr = sf.read(str(input_wav), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    
    max_duration_sec = 300.0  # 5 minutes
    num_samples = int(min(len(data), max_duration_sec * sr))
    sliced_audio = data[:num_samples]
    actual_duration = round(len(sliced_audio) / float(sr), 2)
    
    # Write temp slice for chunked file-based reader if needed
    smoke_wav = smoke_out_dir / "temp_smoke_5min.wav"
    sf.write(str(smoke_wav), sliced_audio, sr)
    
    logger.info(f"Loaded 5-minute smoke audio in-memory ({actual_duration}s, {sr} Hz)")
    
    # 3. Live-call streaming simulation & ASR
    t_start = time.perf_counter()
    
    asr_segments, chunk_metrics, total_dur = transcribe_live_stream_chunks(
        str(smoke_wav),
        max_duration_sec=300.0,
        language="en"
    )
    
    total_chunk_infer_time = sum(c["proc_time_sec"] for c in chunk_metrics)
    asr_rtf = round(total_chunk_infer_time / actual_duration, 4)
    
    # 4. Optimized Diarization with pyannote using in-memory waveform
    diar_time_before_sec = 254.9  # Baseline unoptimized diarization time on CPU
    
    t_diar_start = time.perf_counter()
    diar_segments = diarize_audio(sliced_audio, sample_rate=sr, max_duration_sec=300.0)
    diarization_time_sec = round(time.perf_counter() - t_diar_start, 3)
    diarization_rtf = round(diarization_time_sec / actual_duration, 4)
    
    # 5. Align ASR segments with Diarization
    aligned_segments = align_asr_segments_with_diarization(asr_segments, diar_segments)
    unique_pyannote_speakers = set(d["speaker_id"] for d in diar_segments)
    
    # 6. Speaker name & role resolution (Two-pass dynamic resolution)
    resolver = SpeakerResolver(ticker="SHOP")
    temp_sections = classify_transcript_sections(aligned_segments)
    resolved_segments = resolver.resolve_all_segments(aligned_segments, temp_sections)
    
    # 7. Section classification
    final_sections = classify_transcript_sections(resolved_segments)
    
    total_pipeline_time = round(time.perf_counter() - t_start, 3)
    total_rtf = round(total_pipeline_time / actual_duration, 4)
    
    # Clean up temp file
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
        
    # 9. Estimate total processing time for 12 full captured calls
    # Total audio duration across all 12 calls from capture_manifest.csv = 43,118.7s (~11.98h)
    all_12_audio_duration_sec = 43118.7
    est_asr_time_12_calls_sec = round(all_12_audio_duration_sec * asr_rtf, 1)
    est_diar_time_12_calls_sec = round(all_12_audio_duration_sec * diarization_rtf, 1)
    est_total_time_12_calls_sec = round(all_12_audio_duration_sec * total_rtf, 1)
    est_total_time_12_calls_hrs = round(est_total_time_12_calls_sec / 3600.0, 2)
    
    # 10. Save metrics JSON
    metrics_doc = {
        "ticker": "SHOP",
        "fiscal_period": "Q2 FY2026",
        "audio_duration_sec": actual_duration,
        "asr_infer_time_sec": round(total_chunk_infer_time, 3),
        "asr_rtf": asr_rtf,
        "diarization_time_before_sec": diar_time_before_sec,
        "diarization_time_sec": diarization_time_sec,
        "diarization_rtf": diarization_rtf,
        "total_pipeline_time_sec": total_pipeline_time,
        "total_rtf": total_rtf,
        "chunk_count": len(chunk_metrics),
        "chunk_metrics": chunk_metrics,
        "pyannote_speaker_count": len(unique_pyannote_speakers),
        "pyannote_speakers": sorted(list(unique_pyannote_speakers)),
        "section_counts": {
            sec["type"]: len(sec["segments"]) for sec in final_sections
        },
        "all_12_calls_estimate": {
            "total_audio_duration_sec": all_12_audio_duration_sec,
            "total_audio_duration_hours": round(all_12_audio_duration_sec / 3600.0, 2),
            "estimated_total_time_sec": est_total_time_12_calls_sec,
            "estimated_total_time_hours": est_total_time_12_calls_hrs
        }
    }
    
    out_metrics = smoke_out_dir / "SHOP_Q2_FY2026_metrics.json"
    with open(out_metrics, "w", encoding="utf-8") as f:
        json.dump(metrics_doc, f, indent=2)
        
    # 11. Print comprehensive report
    print("=" * 78)
    print("PHASE 3 STEP 1: RE-RUN SMOKE TEST REPORT (SHOP Q2 FY2026 - 5 MIN)")
    print("=" * 78)
    print(f"Audio Duration: {actual_duration:.1f}s (5.0 min)")
    print(f"Worker CPU Threads: {get_worker_threads()} | PyTorch Threads: {torch.get_num_threads()}")
    print(f"ASR Model: faster-whisper small.en (int8, CPU)")
    print(f"Diarizer: pyannote/speaker-diarization-3.1 (batch_size=32, in-memory)")
    print("-" * 78)
    print("1. DIARIZATION TIME BEFORE vs AFTER:")
    print(f"   - Before Optimization (File read, default batch, default threads): {diar_time_before_sec:.2f}s")
    print(f"   - After Optimization  (In-memory, batch_size=32, max CPU threads): {diarization_time_sec:.2f}s")
    print("-" * 78)
    print("2. SEPARATED RTF & LATENCY METRICS:")
    print(f"   - ASR Processing Time:    {total_chunk_infer_time:.3f}s | asr_rtf:         {asr_rtf:.4f}")
    print(f"   - Diarization Time:       {diarization_time_sec:.3f}s | diarization_rtf: {diarization_rtf:.4f}")
    print(f"   - Total Pipeline Time:    {total_pipeline_time:.3f}s | total_rtf:       {total_rtf:.4f}")
    print(f"   - (Note: 5-minute post-call SLA is evaluated strictly on full-length calls)")
    print("-" * 78)
    print("3. PYANNOTE SPEAKERS DETECTED:")
    print(f"   - Unique pyannote speaker IDs: {len(unique_pyannote_speakers)} {sorted(list(unique_pyannote_speakers))}")
    print("-" * 78)
    print("4. SECTION SEGMENT COUNTS:")
    for sec in final_sections:
        print(f"   - {sec['type']:<17}: {len(sec['segments'])} segments [{sec['start']:.1f}s - {sec['end']:.1f}s]")
    print("-" * 78)
    print("5. FIRST 12 RESOLVED SEGMENTS:")
    for idx, seg in enumerate(resolved_segments[:12]):
        text_preview = seg['text'][:70].replace('\n', ' ')
        print(f"   [{idx+1:>2}] [{seg['start']:>5.1f}s - {seg['end']:>5.1f}s] {seg['speaker_name']:<20} | {seg['speaker_role']:<28} | \"{text_preview}\"")
    print("-" * 78)
    print("6. ESTIMATE OF TOTAL RUNTIME FOR ALL 12 FULL CALLS:")
    print(f"   - Total audio across 12 calls: {all_12_audio_duration_sec:.1f}s ({all_12_audio_duration_sec/3600.0:.2f} hours)")
    print(f"   - Estimated ASR inference time:    {est_asr_time_12_calls_sec:.1f}s ({est_asr_time_12_calls_sec/3600.0:.2f} hours)")
    print(f"   - Estimated Diarization time:      {est_diar_time_12_calls_sec:.1f}s ({est_diar_time_12_calls_sec/3600.0:.2f} hours)")
    print(f"   - Estimated Total Pipeline time:   {est_total_time_12_calls_sec:.1f}s ({est_total_time_12_calls_hrs:.2f} hours)")
    print("=" * 78)
    print(f"Transcript JSON saved to: {out_json}")
    print(f"Metrics JSON saved to:    {out_metrics}")
    print("=" * 78)


if __name__ == "__main__":
    run_smoke_test()
