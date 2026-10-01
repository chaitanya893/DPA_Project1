#!/usr/bin/env python3
"""
ONE-COMMAND REPRODUCIBILITY PIPELINE FOR EARNINGS CALL PROCESSING
================================================================
Executes the complete pipeline in strict sequential order:
  1. Discovery: SEC EDGAR & IR web crawling for 25 target companies
  2. Capture: Audio capture & 16kHz mono WAV standardization (skips existing)
  3. Transcription: 60s streaming chunk ASR + PyAnnote Diarization + Speaker Resolution (skips existing)
  4. Evaluation: Mathematical accuracy scoring & benchmark metric computation
  5. Verification: Automated 0-mismatch cross-report table verification

Flags:
  --sample        : Processes the first 120s of an existing WAV file through the full pipeline
  --call <CALL_ID>: Runs the full pipeline for one existing WAV (e.g. MSFT_Q4_FY2026), ignoring cache, writing only to data/demo/
  --device        : Target compute device ('cuda' or 'cpu', default: auto-detect)
"""

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path
from collections import Counter

# Configure UTF-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

import soundfile as sf
import torch

from config.settings import AUDIO_DIR, TRANSCRIPTS_DIR
from src.utils.logger import setup_logger

logger = setup_logger("run_all")


def check_prerequisites(device: str) -> str:
    """Validates necessary environment variables and hardware accessibility."""
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("\n" + "=" * 80)
        print("ERROR: HF_TOKEN is missing from your environment or .env file.")
        print("Speaker diarization requires a Hugging Face token with access to:")
        print("  - https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("  - https://huggingface.co/pyannote/segmentation-3.0")
        print("Please set HF_TOKEN in your .env file or environment.")
        print("=" * 80 + "\n")
        sys.exit(1)

    if device == "cuda" and not torch.cuda.is_available():
        print("[WARNING] CUDA was requested but torch.cuda.is_available() is False. Falling back to CPU.")
        device = "cpu"

    return device


def find_existing_wav() -> Path:
    """Finds the first valid .wav audio file in data/audio."""
    if not AUDIO_DIR.exists():
        print(f"\nERROR: Audio directory does not exist at {AUDIO_DIR}")
        sys.exit(1)

    wav_files = sorted(list(AUDIO_DIR.glob("*.wav")))
    valid_wavs = [f for f in wav_files if not f.name.startswith("sample_")]
    if not valid_wavs:
        print("\n" + "=" * 80)
        print(f"ERROR: No WAV audio files found in {AUDIO_DIR}")
        print("Please place earnings call WAV files in data/audio/ or run capture first.")
        print("=" * 80 + "\n")
        sys.exit(1)

    return valid_wavs[0]


def find_call_wav(call_id: str) -> Path:
    """Finds the specific .wav audio file in data/audio corresponding to call_id."""
    if not AUDIO_DIR.exists():
        print(f"\nERROR: Audio directory does not exist at {AUDIO_DIR}")
        sys.exit(1)

    clean_id = call_id.replace(".wav", "").replace(".json", "").strip()
    exact_path = AUDIO_DIR / f"{clean_id}.wav"
    if exact_path.exists():
        return exact_path

    # Search matching filenames
    for p in AUDIO_DIR.glob("*.wav"):
        if p.stem.lower() == clean_id.lower() or clean_id.lower() in p.stem.lower():
            return p

    available = [p.stem for p in sorted(AUDIO_DIR.glob("*.wav")) if not p.name.startswith("sample_")]
    print(f"\nERROR: Audio WAV file not found for call '{call_id}' in {AUDIO_DIR}")
    print(f"Available WAV calls: {', '.join(available)}")
    sys.exit(1)


def run_sample_pipeline(device: str) -> None:
    """Runs the full pipeline on the first 120 seconds of an existing audio file."""
    start_time = time.time()
    device = check_prerequisites(device)
    wav_path = find_existing_wav()

    print("\n" + "=" * 80)
    print("  [SAMPLE PIPELINE] EXECUTING 120-SECOND FULL PIPELINE SAMPLE")
    print(f"  Source Audio: {wav_path.name}")
    print(f"  Target Device: {device.upper()}")
    print("=" * 80)

    # 1. Slice first 120s of audio
    sample_wav_path = AUDIO_DIR / "sample_120s.wav"
    print(f"\n[1/4] Extracting first 120 seconds of audio from {wav_path.name}...")
    audio_data, sr = sf.read(str(wav_path))
    max_frames = int(120.0 * sr)
    sample_data = audio_data[:max_frames]
    sf.write(str(sample_wav_path), sample_data, sr, subtype="PCM_16")
    actual_dur = len(sample_data) / sr
    print(f"      [OK] Saved 120s sample WAV ({actual_dur:.1f}s, {sr}Hz) -> {sample_wav_path}")

    # 2. Transcribe using streaming chunked ASR
    print(f"\n[2/4] Running 60s streaming chunk ASR (faster-whisper small.en on {device})...")
    from src.transcription.asr_engine import transcribe_live_stream_chunks, get_whisper_model
    compute_type = "float16" if device == "cuda" else "int8"
    get_whisper_model(model_size="small.en", compute_type=compute_type, device=device)
    asr_segments, chunk_metrics, total_dur = transcribe_live_stream_chunks(
        wav_path=str(sample_wav_path)
    )
    asr_infer_time = sum(c["proc_time_sec"] for c in chunk_metrics)
    print(f"      [OK] Generated {len(asr_segments)} ASR segments in {asr_infer_time:.2f}s (RTF: {asr_infer_time/actual_dur:.4f})")

    # 3. Run PyAnnote Diarization
    print(f"\n[3/4] Running PyAnnote Speaker Diarization on {device}...")
    from src.transcription.diarizer import diarize_audio, align_asr_segments_with_diarization
    diar_t0 = time.time()
    diar_turns = diarize_audio(str(sample_wav_path))
    diar_dur = round(time.time() - diar_t0, 2)
    print(f"      [OK] Diarization complete in {diar_dur:.2f}s ({len(diar_turns)} speaker turns identified)")

    # 4. Align, Resolve Speakers & Split Sections
    print(f"\n[4/4] Aligning Diarization, Resolving Speakers & Classifying Sections...")
    aligned_segments = align_asr_segments_with_diarization(asr_segments, diar_turns)

    ticker = "MSFT" if "MSFT" in wav_path.stem else ("SHOP" if "SHOP" in wav_path.stem else "MSFT")
    from src.transcription.speaker_resolver import SpeakerResolver
    from src.transcription.section_splitter import classify_transcript_sections

    temp_sections = classify_transcript_sections(aligned_segments)
    resolver = SpeakerResolver(ticker=ticker)
    resolved_segments = resolver.resolve_all_segments(aligned_segments, temp_sections)
    sections = classify_transcript_sections(resolved_segments)

    samples_dir = PROJECT_ROOT / "data" / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    output_json_path = samples_dir / "sample_120s.json"

    transcript_doc = {
        "event_id": f"{ticker}_SAMPLE_120S",
        "ticker": ticker,
        "fiscal_period": "Sample 120s",
        "audio_source": str(wav_path.name),
        "duration_sec": round(actual_dur, 2),
        "sections": sections,
        "segments": resolved_segments,
        "pipeline": {
            "device": device,
            "asr_model": "faster-whisper small.en",
            "asr_infer_time_sec": round(asr_infer_time, 2),
            "diarization_time_sec": round(diar_dur, 2),
            "total_elapsed_sec": round(time.time() - start_time, 2)
        }
    }

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(transcript_doc, f, indent=2, ensure_ascii=False)

    total_time = round(time.time() - start_time, 2)
    print("\n" + "=" * 80)
    print(f"  [SUCCESS] SAMPLE PIPELINE COMPLETE IN {total_time}s")
    print(f"  [OUTPUT FILE] {output_json_path.resolve()}")
    print(f"  [SEGMENTS] Processed {len(resolved_segments)} segments across {len(sections)} sections.")
    print("=" * 80 + "\n")


def run_call_demo(call_id: str, device: str) -> None:
    """
    Runs the FULL pipeline (ASR + PyAnnote Diarization + Speaker Resolution + Sections)
    for ONE existing call audio WAV, IGNORING any cached files, and writing output ONLY
    to data/demo/<CALL_ID>.json and data/demo/<CALL_ID>_metrics.json.
    """
    start_time = time.time()
    device = check_prerequisites(device)
    wav_path = find_call_wav(call_id)
    call_key = wav_path.stem

    # Parse ticker and fiscal period
    if call_key.startswith("MSFT_"):
        ticker = "MSFT"
        fiscal_period = call_key[5:].replace("_", " ")
    elif call_key.startswith("SHOP_"):
        ticker = "SHOP"
        fiscal_period = call_key[5:].replace("_", " ")
    else:
        parts = call_key.split("_")
        ticker = parts[0]
        fiscal_period = " ".join(parts[1:])

    # Load verified call date if available
    from src.transcription.pipeline import load_call_dates_and_sources
    date_info_map = load_call_dates_and_sources()
    date_info = date_info_map.get(f"{ticker}_{fiscal_period}", {})
    call_dt = date_info.get("call_datetime_utc", None)

    print("\n" + "=" * 80)
    print(f"  [CALL DEMO] RUNNING FULL END-TO-END DEMO FOR: {call_key}")
    print(f"  Audio Source:   {wav_path.name}")
    print(f"  Target Device:  {device.upper()}")
    print(f"  Cache Status:   IGNORED (Live Full Processing)")
    print(f"  Output Target:  data/demo/ ONLY")
    print("=" * 80)

    # 1. 60-s Streaming Chunk ASR (Live with progress per chunk)
    print(f"\n[1/4] Running 60s Streaming Chunk ASR (faster-whisper small.en on {device})...")
    from src.transcription.asr_engine import transcribe_live_stream_chunks, get_whisper_model
    compute_type = "float16" if device == "cuda" else "int8"
    get_whisper_model(model_size="small.en", compute_type=compute_type, device=device)

    def on_chunk(chunk_idx, total_chunks, start_s, end_s, proc_t, rtf):
        print(f"      [Chunk {chunk_idx:>2}/{total_chunks:>2}] {start_s:>6.1f}s – {end_s:>6.1f}s | Proc: {proc_t:>5.2f}s | RTF: {rtf:.4f}")

    asr_segments, chunk_metrics, total_audio_dur = transcribe_live_stream_chunks(
        wav_path=str(wav_path),
        progress_callback=on_chunk
    )
    asr_infer_time = sum(c["proc_time_sec"] for c in chunk_metrics)
    asr_rtf = round(asr_infer_time / max(0.001, total_audio_dur), 4)
    print(f"      [OK] ASR complete: {len(asr_segments)} segments in {asr_infer_time:.2f}s (ASR RTF: {asr_rtf:.4f})")

    # 2. PyAnnote Speaker Diarization (Live inference)
    print(f"\n[2/4] Running PyAnnote Speaker Diarization on {device}...")
    from src.transcription.diarizer import diarize_audio, align_asr_segments_with_diarization
    t_diar_start = time.perf_counter()
    diar_turns = diarize_audio(str(wav_path))
    diar_duration = round(time.perf_counter() - t_diar_start, 2)
    diar_rtf = round(diar_duration / max(0.001, total_audio_dur), 4)
    print(f"      [OK] Diarization complete in {diar_duration:.2f}s ({len(diar_turns)} turns, Diar RTF: {diar_rtf:.4f})")

    # 3. Align Diarization, Speaker Name & Role Resolution, and Section Classification
    print(f"\n[3/4] Aligning Diarization, Resolving Speakers & Classifying Sections...")
    t_res_start = time.perf_counter()
    aligned_segments = align_asr_segments_with_diarization(asr_segments, diar_turns)

    from src.transcription.speaker_resolver import SpeakerResolver
    from src.transcription.section_splitter import classify_transcript_sections

    temp_sections = classify_transcript_sections(aligned_segments)
    resolver = SpeakerResolver(ticker=ticker)
    resolved_segments = resolver.resolve_all_segments(aligned_segments, temp_sections)
    sections = classify_transcript_sections(resolved_segments)
    res_duration = round(time.perf_counter() - t_res_start, 3)

    sec_counts = {s["type"]: len(s["segments"]) for s in sections}
    qa_count = sec_counts.get("qa", 0)

    # 4. Latency & Metrics Calculations
    total_time = round(time.time() - start_time, 2)
    total_rtf = round((asr_infer_time + diar_duration) / max(0.001, total_audio_dur), 4)
    queue_drained = all(c["proc_time_sec"] < c["duration_sec"] for c in chunk_metrics)
    last_chunk_proc = chunk_metrics[-1]["proc_time_sec"] if chunk_metrics else 0.0
    post_call_latency = round(last_chunk_proc + diar_duration + res_duration + 0.15, 3)
    sla_status = "PASS" if (queue_drained and post_call_latency <= 300.0) else "FAIL"

    # 5. Write ONLY to data/demo/
    demo_dir = PROJECT_ROOT / "data" / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    json_out_path = demo_dir / f"{call_key}.json"
    metric_out_path = demo_dir / f"{call_key}_metrics.json"

    transcript_doc = {
        "event_id": f"DEMO_{call_key}",
        "ticker": ticker,
        "fiscal_period": fiscal_period,
        "call_datetime_utc": call_dt,
        "audio_source": str(wav_path.name),
        "duration_sec": round(total_audio_dur, 2),
        "sections": sections,
        "segments": resolved_segments,
        "pipeline": {
            "asr_model": f"faster-whisper-small.en-{compute_type}",
            "diarizer": "pyannote/speaker-diarization-3.1",
            "device": device,
            "asr_infer_time_sec": round(asr_infer_time, 3),
            "diarization_time_sec": round(diar_duration, 3),
            "resolution_time_sec": round(res_duration, 3),
            "total_elapsed_sec": round(total_time, 3)
        }
    }

    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(transcript_doc, f, indent=2, ensure_ascii=False)

    all_dropped_segs = [seg for c in chunk_metrics for seg in c.get("dropped_segments", [])]
    metrics_doc = {
        "ticker": ticker,
        "fiscal_period": fiscal_period,
        "call_datetime_utc": call_dt,
        "audio_path": f"data/audio/{wav_path.name}",
        "audio_duration_sec": round(total_audio_dur, 2),
        "asr_infer_time_sec": round(asr_infer_time, 3),
        "asr_rtf": asr_rtf,
        "diarization_time_sec": round(diar_duration, 3),
        "diarization_rtf": diar_rtf,
        "resolution_time_sec": round(res_duration, 3),
        "total_pipeline_time_sec": round(total_time, 3),
        "total_rtf": total_rtf,
        "queue_drained": queue_drained,
        "post_call_latency_sec": post_call_latency,
        "sla_status": sla_status,
        "chunk_count": len(chunk_metrics),
        "qa_segments": qa_count,
        "section_counts": sec_counts,
        "pyannote_speakers": sorted(list(set(d["speaker_id"] for d in diar_turns))),
        "dropped_segments": all_dropped_segs,
        "chunk_metrics": chunk_metrics
    }

    with open(metric_out_path, "w", encoding="utf-8") as f:
        json.dump(metrics_doc, f, indent=2, ensure_ascii=False)

    # Top speakers summary
    speaker_counts = Counter()
    for s in resolved_segments:
        spk_id = s.get("speaker_id", "UNKNOWN")
        spk_name = s.get("speaker_name") or "Unknown"
        spk_role = s.get("speaker_role") or "Unknown"
        speaker_counts[(spk_id, spk_name, spk_role)] += 1
    top_speakers = speaker_counts.most_common(6)

    # 6. Print Comprehensive Summary
    print("\n" + "=" * 80)
    print(f"  [DEMO SUCCESS] CALL {call_key} COMPLETED IN {total_time:.2f}s")
    print("=" * 80)
    print(f"  ⏱️  Total Elapsed Time:    {total_time:.2f}s (Audio Duration: {total_audio_dur/60.0:.1f} min)")
    print(f"  🎙️  ASR Inference Time:    {asr_infer_time:.2f}s (ASR RTF: {asr_rtf:.4f})")
    print(f"  👥  Diarization Time:      {diar_duration:.2f}s (Diar RTF: {diar_rtf:.4f})")
    print(f"  ⚡  Post-Call Latency:     {post_call_latency:.2f}s (5-Min SLA: {sla_status})")
    print(f"  📑  Section Counts:        Intro: {sec_counts.get('operator_intro', 0)}, Remarks: {sec_counts.get('prepared_remarks', 0)}, Q&A: {sec_counts.get('qa', 0)}")
    print(f"  🗣️  Top Speakers:")
    for (spk_id, spk_name, spk_role), cnt in top_speakers:
        print(f"      - {spk_id:<10} | {spk_name:<24} | {spk_role:<12} ({cnt} segments)")
    print(f"\n  📁  Deliverable Files (Written ONLY to data/demo/):")
    print(f"      - Transcript: {json_out_path.resolve()}")
    print(f"      - Metrics:    {metric_out_path.resolve()}")
    print("=" * 80 + "\n")


def run_full_pipeline(device: str) -> None:
    """Executes the complete end-to-end earnings call pipeline."""
    start_total = time.time()
    device = check_prerequisites(device)

    print("\n" + "=" * 80)
    print("  [PIPELINE] EXECUTING COMPLETE END-TO-END EARNINGS PIPELINE")
    print(f"  Device: {device.upper()}")
    print("=" * 80)

    # 1. Phase 1: Event Discovery
    print("\n[PHASE 1/5] Running Event Discovery across 25 Companies...")
    from src.discovery.pipeline import run_discovery_pipeline
    events = run_discovery_pipeline()
    print(f"            [OK] Discovery complete ({len(events)} events in registry).")

    # 2. Phase 2: Audio Capture (skips existing files)
    print("\n[PHASE 2/5] Running Audio Capture & 16kHz WAV Standardization (skips existing)...")
    from src.capture.pipeline import run_capture_pipeline
    manifest_path = run_capture_pipeline()
    print(f"            [OK] Audio capture manifest verified at: {manifest_path}")

    # 3. Phase 3: Transcription Pipeline (skips calls with existing JSON)
    print("\n[PHASE 3/5] Running Streaming Transcription Pipeline (skips completed calls)...")
    from src.transcription.pipeline import run_phase3_pipeline
    run_phase3_pipeline()
    print(f"            [OK] Transcription pipeline execution complete.")

    # 4. Phase 4: Evaluation & Part B Benchmark Computation
    print("\n[PHASE 4/5] Running Evaluation & Benchmark Part B Computation...")
    from scripts.compute_part_b import compute_part_b_metrics
    b_metrics = compute_part_b_metrics()
    print(f"            [OK] Evaluated 10 MSFT calls (Mean DER: {b_metrics['mean_der']}%, Speaker Acc: {b_metrics['pooled_speaker']['overall_acc']}%).")

    # 5. Verification: Verify all report tables programmatically
    print("\n[PHASE 5/5] Running Automated Report Verification across all docs...")
    from scripts.verify_reports import verify_latency_report, verify_accuracy_report, verify_benchmark_part_b
    lat_mismatches = verify_latency_report()
    acc_mismatches = verify_accuracy_report()
    part_b_mismatches = verify_benchmark_part_b()
    total_mismatches = lat_mismatches + acc_mismatches + part_b_mismatches

    total_time = round(time.time() - start_total, 2)
    print("\n" + "=" * 80)
    if total_mismatches == 0:
        print(f"  [SUCCESS] FULL PIPELINE COMPLETE IN {total_time}s (0 MISMATCHES)")
        print(f"  Reports Generated & Verified:")
        print(f"    - docs/latency_report.md")
        print(f"    - docs/accuracy_report.md")
        print(f"    - docs/benchmark_part_b.md")
    else:
        print(f"  [WARNING] PIPELINE COMPLETED WITH {total_mismatches} VERIFICATION MISMATCHES.")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="One-Command Financial Earnings Audio Transcription Pipeline")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Process only the first 120s of an existing audio WAV file through the full pipeline"
    )
    parser.add_argument(
        "--call",
        type=str,
        default=None,
        help="Process one specific full earnings call WAV through the pipeline (ignoring cache, writing ONLY to data/demo/)"
    )
    parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu"],
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Compute device for ASR and PyAnnote diarization ('cuda' or 'cpu')"
    )

    args = parser.parse_args()

    if args.call:
        run_call_demo(call_id=args.call, device=args.device)
    elif args.sample:
        run_sample_pipeline(device=args.device)
    else:
        run_full_pipeline(device=args.device)


if __name__ == "__main__":
    main()
