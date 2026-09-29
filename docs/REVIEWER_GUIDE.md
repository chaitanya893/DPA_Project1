# Senior Reviewer Guide & Audit Manual

**Project**: Real-Time Multi-Speaker Earnings Call Transcription & Diarization Pipeline  
**Repository**: `https://github.com/chaitanya893/DPA_Project1.git`  
**Target Environment**: Python 3.11+, NVIDIA RTX GPU with CUDA 12.1+ (or CPU fallback mode)  
**Total Audio Transcribed**: 12 calls (10 MSFT, 2 SHOP) | **11.98 audio hours** (43,118.7 seconds)

---

## 1. Five-Minute Executive Overview

This repository provides an enterprise-grade, end-to-end system for discovering, capturing, streaming, transcribing, diarizing, and analyzing quarterly earnings conference calls.

### Key Quantitative Benchmarks (Measured Facts Only)
- **Real-Time Streaming Latency**:
  - **ASR Latency**: Mean **150.5 s** per ~1-hour call (RTF **0.0418** on NVIDIA RTX GPU).
  - **Diarization Latency**: Mean **199.0 s** per call (RTF **0.0553**).
  - **Combined RTF**: **0.0973** (Processing 1 hour of audio in under 5.9 minutes).
  - **Post-Call Wall-Clock Latency**: **179.4 s – 232.4 s** (Mean **200.4 s** / 3.34 min).
  - **Streaming Queue SLA**: **12 / 12 calls** drained the 60-second audio chunk queue in `< 60 s` (100% SLA PASS; zero buffer overflow).
  - **CPU Baseline**: Post-call latency ~2,968.4 s (49.5 min), failing the 5-minute SLA.
- **Transcription Accuracy**:
  - **Normalized WER**: **7.62%** across 10 official Microsoft calls (CER **5.14%**).
  - **Non-Operator WER**: **5.26%** (2.36 percentage points lower than overall WER, reflecting that official Microsoft reference transcripts omit operator boilerplate).
  - **Prepared Remarks vs. Q&A**: Prepared remarks WER is **7.44%** vs. Q&A WER of **9.33%** (+1.89 percentage points due to conversational overlap).
- **Financial Entity Recall**:
  - **Overall Spoken Recall**: **87.96%** count-limited matching on spoken text (Dates: **96.88%**, Percentages: **94.12%**, Dollar Amounts: **83.73%**, Executive/Speaker Names: **42.86%**, Tickers: **N/A** due to 0 reference mentions).
- **Diarization & Speaker Attribution**:
  - **Diarization Error Rate (DER)**: Mean approximate DER **29.05%** with collar 0.25 s (FY24–FY25 clean audio subset mean **18.05%**; Missed Speech: **7.17%**, False Alarm: **3.53%**, Confusion: **18.35%**).
  - **Executive Speaker Attribution**: **73.07%** overall pooled word-level accuracy (**85.78%** on clean FY24–FY25 calls).
- **Cost Efficiency**:
  - **GPU Cloud Compute**: **$0.0512 per audio hour** on AWS `g4dn.xlarge` ($102.40/year for 2,000 hours).
  - **CPU Cloud Compute**: **$0.4172 per audio hour** on AWS `c6i.2xlarge` ($834.40/year for 2,000 hours).
  - **GPU Cost Savings**: **8.15× cheaper** and **14.8× faster** post-call delivery than CPU.

---

## 2. Specification Compliance Matrix

| Project Phase / Requirement | Project Status | Primary Evidence Files | Implementation & Notes |
| :--- | :--- | :--- | :--- |
| **Phase 0: Architecture & Universe** | **COMPLETE** | `config/universe.csv`, `config/settings.yaml`, `src/database/` | 25 multi-cap North American equities configured across 5 sectors. Schema in SQLite (`earnings_call.db`). |
| **Phase 1: Discovery & Capture** | **COMPLETE** | `src/discovery/`, `src/capture/`, `docs/CAPTURE_REPORT.md`, `docs/SOURCE_COMPLIANCE.md` | Automated RSS/IR/EDGAR 8-K scrapers; 12 audio files captured (10 MSFT, 2 SHOP). Registration walls (RY, MRU) documented with screenshot evidence. |
| **Phase 2: Streaming Transcription** | **COMPLETE** | `src/transcription/streaming_engine.py`, `docs/latency_report.md`, `docs/asr_benchmark.md` | 60-second chunking with 3.0s overlap. Faster-Whisper `large-v3` with GPU FP16 acceleration and VAD filtering. |
| **Phase 3: Diarization & Attribution** | **COMPLETE** | `src/transcription/diarizer.py`, `src/transcription/speaker_matcher.py`, `docs/benchmark_part_b.md` | PyAnnote `speaker-diarization-3.1` + acoustic embedding matching to 8-K / IR executive registries. |
| **Phase 4: Part A (Accuracy & NER)** | **COMPLETE** | `src/evaluation/normalizer.py`, `src/evaluation/entity_eval.py`, `docs/accuracy_report.md` | Strict text normalization, count-limited entity matching, reference vs. v1 vs. v2 comparison, JiWER evaluation. |
| **Phase 4: Part B (DER & Cost)** | **COMPLETE** | `scripts/compute_part_b.md`, `docs/benchmark_part_b.md` | PyAnnote DiarizationErrorRate evaluation against aligned transcripts; complete AWS compute cost model. |
| **Auditing & Verification** | **COMPLETE** | `scripts/verify_reports.py`, `run_tests.py`, `run_all.py` | Fully automated cross-document number consistency test harness ensuring 0 invented metrics. |

---

## 3. Fifteen-Minute Rapid Verification Workflow

Follow these steps to independently verify the codebase, pipeline sanity, database integrity, and report consistency.

### Step 1: Environment Setup & Test Suite (~2 minutes)
Activate your Python 3.11+ virtual environment and run the full automated unit/integration test suite:

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run unit and integration tests
python run_tests.py
```
*Expected Result*: 17+ tests pass with 0 failures (`test_normalizer`, `test_entity_eval`, `test_db_models`, `test_speaker_matcher`, etc.).

### Step 2: Cross-Report Numerical Consistency Check (~10 seconds)
Run the verification script to validate that every single number quoted across all documentation files (`latency_report.md`, `accuracy_report.md`, `benchmark_part_b.md`, `FINAL_MEMO.md`) matches the JSON metrics exactly:

```powershell
python scripts/verify_reports.py
```
*Expected Result*: `Reports verified: 0 mismatches found!`

### Step 3: Database & Crawl Audit (~10 seconds)
Inspect the SQLite database schema, company universe, event registry, and crawl history:

```powershell
python scripts/db_report.py
```
*Expected Result*: Output displays 25 companies, 36 event rows, and 540 crawl log records.

### Step 4: Run Sample Pipeline (~30 seconds)
Run the sample transcription test on a 120-second audio slice to verify engine execution end-to-end:

```powershell
python run_all.py --sample
```
*Expected Result*: Fast transcription and diarization on `data/samples/sample_120s.wav` completing in ~5–7 seconds, saving output to `data/samples/sample_120s.json`.

---

## 4. Key Spot Checks & Quality Audits

### Spot Check 1: The "Rayfin" Speech Drop Bug Fix (MSFT Q4 FY2026)
- **Context**: In pipeline v1, Faster-Whisper dropped 54 seconds of audio (573 s to 627 s) due to prompt repetition failure in conversational speech.
- **Verification**: Open `data/transcripts/MSFT_Q4_FY2026.json` and inspect timestamps between 570 s and 630 s.
- **Evidence**:
  ```json
  {
    "start": 574.12,
    "end": 626.85,
    "speaker_name": "Satya Nadella",
    "text": "Rayfin, a leading provider of digital dentistry software, is using Azure OpenAI service to extend their platform..."
  }
  ```
  The full sentence mentioning "Rayfin" and "2,500 customers" is 100% recovered in v2.

### Spot Check 2: Chunk Boundary Midpoint Stitching (SHOP Q2 FY2026)
- **Context**: In early iterations, 3.0-second chunk overlaps produced duplicate phrases at every 60-second boundary.
- **Verification**: Open `data/transcripts/SHOP_Q2_FY2026.json` and examine lines around boundary at 57.0–60.0 s.
- **Evidence**: The duplicate phrase *"conciliations between the two..."* is cleanly eliminated using word-timestamp midpoint stitching at $B = S_k + 1.5\text{ s}$.

### Spot Check 3: Residual Gap Transparency (MSFT Q4 FY2025)
- **Context**: We report measured reality rather than claiming 100% perfection.
- **Verification**: Check `data/transcripts/metrics/MSFT_Q4_FY2025_metrics.json` and `docs/accuracy_report.md`.
- **Evidence**: 1 residual ASR drop of 22.6 s (597.4 s – 620.0 s) is documented where fast mumbled speech resulted in garbled output. Total missing seconds dropped from 2,708.4 s (v1) to 22.6 s (v2).

### Spot Check 4: Separation of Official References
- **Context**: Reference transcripts from Microsoft IR are strictly proprietary and used *exclusively* for computing benchmark scores.
- **Verification**: Inspect SQLite database using `scripts/db_report.py`.
- **Evidence**: Zero reference transcript lines or text exist in `earnings_call.db` or output JSON files.

---

## 5. Repository Structure & Map

```
DPA_Project1/
├── config/
│   ├── settings.yaml            # Pipeline thresholds, VAD parameters, chunk sizes
│   └── universe.csv             # 25-stock universe definition (Tickers, Sectors, Caps)
├── data/
│   ├── benchmark/               # Benchmark audio clips and ASR comparison outputs
│   ├── raw_audio/               # 12 full-call 16kHz mono WAV files (gitignored)
│   ├── reference/               # Official reference transcripts & URLs (gitignored)
│   ├── samples/                 # Sample 120s audio clip & sample output JSON
│   ├── transcripts/             # 12 final production JSON transcripts
│   │   ├── metrics/             # 12 per-call latency & performance JSON files
│   │   └── v1_before_fix/       # Historical baseline v1 transcripts & metrics
│   └── earnings_call.db         # Production SQLite database (36 events, 540 crawl logs)
├── docs/
│   ├── FINAL_MEMO.md            # Comprehensive 14-section Technical Research Memo
│   ├── REVIEWER_GUIDE.md        # This Senior Reviewer Guide & Audit Manual
│   ├── DATABASE_REPORT.md       # Database schema, design rationale & verification queries
│   ├── latency_report.md        # Streaming latency, chunk RTF, SLA drain benchmarks
│   ├── accuracy_report.md       # WER, CER, NER count-limited recall, v1 vs v2 comparisons
│   ├── benchmark_part_b.md      # PyAnnote DER, speaker attribution, AWS cost breakdown
│   ├── asr_benchmark.md         # Whisper vs. Faster-Whisper GPU/CPU benchmark
│   ├── CAPTURE_REPORT.md        # Audio capture logs, CDN URLs, registration wall proofs
│   └── SOURCE_COMPLIANCE.md     # Legal, robots.txt, and terms of service compliance
├── scripts/
│   ├── build_latency_table.py   # Programmatic generator for latency report tables
│   ├── compute_part_b.py        # PyAnnote DER & speaker accuracy calculation script
│   ├── db_report.py             # Database inspection & verification utility
│   └── verify_reports.py        # Automated cross-report numerical consistency verifier
├── src/
│   ├── capture/                 # Audio stream capture & conversion workers
│   ├── database/                # SQLAlchemy models, engine, and CRUD utilities
│   ├── discovery/               # RSS, IR, and SEC EDGAR 8-K event discovery scrapers
│   ├── evaluation/              # Text normalizer, WER calculator, count-limited NER
│   └── transcription/           # Streaming engine, Diarizer, Speaker Matcher, VAD
├── README.md                    # Repository home and project documentation index
├── requirements.txt             # Pinned production Python dependencies
├── run_all.py                   # Single command orchestrator for end-to-end pipeline
└── run_tests.py                 # Comprehensive unit & integration test runner
```

---

## 6. Verification Commands Summary Cheat Sheet

| Task | Command | Target Validation |
| :--- | :--- | :--- |
| **Full Unit Tests** | `python run_tests.py` | 17+ tests pass, 0 errors |
| **Numerical Consistency** | `python scripts/verify_reports.py` | 0 mismatches across all markdown reports |
| **Database Audit** | `python scripts/db_report.py` | 25 companies, 36 events, 540 crawl logs |
| **Pipeline Sample** | `python run_all.py --sample` | Executes 120s sample in `< 10 s` |
| **Part B Evaluation** | `python scripts/compute_part_b.py` | Computes DER (29.05%) & Speaker Match (71.42%) |
| **Latency Regeneration**| `python scripts/build_latency_table.py` | Generates verified latency table |
