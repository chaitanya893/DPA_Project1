import time
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.discovery.pipeline import run_discovery_pipeline
from src.capture.pipeline import run_capture_pipeline
from src.transcription.pipeline import run_transcription_pipeline
from src.benchmark.evaluator import run_benchmark_evaluation
from src.benchmark.memo_generator import generate_final_memo
from src.utils.logger import setup_logger

logger = setup_logger("run_all")


def run_full_pipeline():
    """Executes the entire end-to-end pipeline from Phase 0 to Phase 4 in a single command."""
    start_total = time.time()

    print("\n" + "=" * 80)
    print("  [PIPELINE] EXECUTING END-TO-END EARNINGS CALL CAPTURE & BENCHMARK PIPELINE")
    print("=" * 80)

    # 1. Phase 1: Event Discovery
    print("\n[PHASE 1/4] Running Event Discovery across 25 Companies...")
    events = run_discovery_pipeline()
    print(f"            [OK] Successfully populated event_registry for {len(events)} companies.")

    # 2. Phase 2: Audio Capture
    print("\n[PHASE 2/4] Running Audio Capture and 16kHz WAV Standardization...")
    manifest_path = run_capture_pipeline()
    print(f"            [OK] Audio capture manifest generated at: {manifest_path}")

    # 3. Phase 3: Transcription Pipeline
    print("\n[PHASE 3/4] Running Streaming ASR Transcription & Speaker Diarization...")
    json_transcripts = run_transcription_pipeline()
    print(f"            [OK] Generated {len(json_transcripts)} structured JSON transcripts.")

    # 4. Phase 4: Benchmarking & Final Memo Generation
    print("\n[PHASE 4/4] Running Mathematical Evaluation & Final Research Memo Generation...")
    memo_path = generate_final_memo()
    print(f"            [OK] Final 5-8 Page Research Memo generated at: {memo_path}")

    total_time = round(time.time() - start_total, 2)
    print("\n" + "=" * 80)
    print(f"  [SUCCESS] PIPELINE EXECUTION COMPLETE IN {total_time}s!")
    print(f"  [REPORT] Read Final Memo: docs/FINAL_MEMO.md")
    print(f"  [REPORT] Read Benchmark Report: docs/benchmark_report.md")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_full_pipeline()
