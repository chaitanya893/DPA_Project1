# Financial Earnings Audio Transcription & Diarization Pipeline

> **Core Project Deliverables & Audit Guides**:
> - 📄 **[Technical Research Memo (14 Sections)](docs/FINAL_MEMO.md)**: Complete architectural, quantitative, and cost analysis memo.
> - 🔍 **[Senior Reviewer & Audit Guide](docs/REVIEWER_GUIDE.md)**: 5-minute overview, PDF compliance matrix, 15-minute verification steps, spot checks, and repository map.
> - 🗄️ **[Database & Discovery Report](docs/DATABASE_REPORT.md)**: Schema inspection, SQLite vs PostgreSQL rationale, SEC EDGAR discovery logs, and query audit.

An end-to-end data engineering, streaming speech recognition (ASR), and speaker diarization pipeline designed for corporate earnings calls. The system discovers quarterly earnings events from SEC EDGAR and investor relations sites, captures audio streams to standardized 16 kHz Mono WAV format, transcribes speech with word-level overlap stitching and hallucination filtering, diarizes and resolves speakers into executive roles and analysts, and programmatically benchmarks latency, accuracy, and production economics.

---

## 🚀 One-Command Execution

Run the complete end-to-end pipeline (Discovery → Capture → Transcription → Evaluation → Verification) with a single command:

```bash
# Full pipeline on GPU (skips already captured/transcribed calls)
python run_all.py --device cuda

# Or on CPU
python run_all.py --device cpu
```

### 120-Second Verification Sample
To test the full streaming ASR, PyAnnote diarization, speaker resolution, and section classification pipeline on a short sample:

```bash
python run_all.py --sample --device cuda
```
* **Output Path**: `data/samples/sample_120s.json`
* **Measured Sample Runtime**: ~24.1s (RTF 0.20 on RTX 4050 Laptop GPU / CUDA)

---

## 🛠️ Setup & Installation

### 1. Prerequisites
* **Python**: Version `3.11` recommended (3.11.x or 3.12.x supported)
* **FFmpeg**: Must be installed and available in system `PATH` (for audio standardization).

### 2. Virtual Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

### 3. Install PyTorch & Dependencies
For **GPU Acceleration (CUDA 12.1)**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

For **CPU-Only Execution**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

*(Note: WhisperX is maintained separately in `.venv_whisperx` for isolated ASR benchmark comparisons.)*

### 4. Hugging Face Access & Environment Configuration
1. Accept the user conditions on Hugging Face for the following models:
   * [`pyannote/speaker-diarization-3.1`](https://huggingface.co/pyannote/speaker-diarization-3.1)
   * [`pyannote/segmentation-3.0`](https://huggingface.co/pyannote/segmentation-3.0)
2. Create a `.env` file in the project root:
```ini
HF_TOKEN=your_huggingface_token_here
CONTACT_EMAIL=your_email@domain.com
# Database URL (defaults to SQLite earnings_call.db if omitted)
# DATABASE_URL=postgresql://user:password@localhost:5432/earnings_call
```

---

## 📊 Measured Performance & Pipeline Metrics

All figures below are drawn directly from the automated metrics files and verified reports:

| Metric Category | Measured Pipeline Value | Primary Report Source |
| :--- | :--- | :--- |
| **Processed Dataset** | 12 calls (10 Microsoft, 2 Shopify) = **11.98 audio hours** ($43,115.6\text{s}$) | `docs/latency_report.md` |
| **Total Pipeline RTF (GPU)** | **0.0973 RTF** (Average total processing time = $350.2\text{s}$ per audio hour) | `docs/latency_report.md` |
| **ASR Inference Time (GPU)** | **150.7s / audio hour** (RTF 0.0419, `faster-whisper small.en float16`) | `docs/latency_report.md` |
| **Diarization Time (GPU)** | **199.4s / audio hour** (RTF 0.0554, `pyannote/speaker-diarization-3.1`) | `docs/latency_report.md` |
| **Streaming Post-Call Latency** | **179.38s – 232.35s** (100% PASS on the 300s SLA, queue drained) | `docs/latency_report.md` |
| **Word Error Rate (Normalized WER)** | **7.62%** average across 10 MSFT calls (Raw WER 18.06%, CER 5.16%) | `docs/accuracy_report.md` |
| **Non-Operator Spoken WER** | **5.26%** (excluding operator conference greetings) | `docs/accuracy_report.md` |
| **Financial Entity Recall** | **88.94%** overall count-limited recall (Dates: 96.88%, %: 94.12%, \$: 83.73%) | `docs/accuracy_report.md` |
| **Approximate DER (MSFT)** | **29.05%** macro average (FY24–25 average: **18.05%**, Missed: 7.17%, FA: 3.53%) | `docs/benchmark_part_b.md` |
| **Executive Speaker Accuracy** | **73.07%** pooled / **85.78%** in FY24–25 (Satya Nadella, Amy Hood, IR) | `docs/benchmark_part_b.md` |
| **GPU Cost per Audio Hour** | **$0.0512 / audio hour** (AWS EC2 `g4dn.xlarge` NVIDIA T4 @ $0.526/hr) | `docs/benchmark_part_b.md` |
| **Annual 500-Company Cost** | **$102.40 / year** for 2,000 audio hours ($834.40 on CPU) | `docs/benchmark_part_b.md` |

---

## 📁 Artifact Locations & Deliverables

* **Structured Transcript Outputs**: [`data/transcripts/`](file:///c:/Users/chait/Desktop/DPA_Project1/data/transcripts)
  * `MSFT_Q*.json` (10 calls)
  * `SHOP_Q*.json` (2 calls)
* **Call Metrics JSON**: [`data/transcripts/metrics/`](file:///c:/Users/chait/Desktop/DPA_Project1/data/transcripts/metrics) (`*_metrics.json`)
* **Audio Capture Manifest**: [`data/audio/capture_manifest.csv`](file:///c:/Users/chait/Desktop/DPA_Project1/data/audio/capture_manifest.csv)
* **Published Reports & Benchmarks**:
  * [`docs/latency_report.md`](file:///c:/Users/chait/Desktop/DPA_Project1/docs/latency_report.md): 12-call latency, RTF breakdown, queue drain verification, and 300s SLA status.
  * [`docs/accuracy_report.md`](file:///c:/Users/chait/Desktop/DPA_Project1/docs/accuracy_report.md): Word/character error rates, jiwer breakdown, operator greeting impact, and financial entity recall.
  * [`docs/benchmark_part_b.md`](file:///c:/Users/chait/Desktop/DPA_Project1/docs/benchmark_part_b.md): Approximate DER, speaker-name identification accuracy, cloud GPU/CPU cost modeling, and subgroup analysis.
  * [`docs/asr_benchmark.md`](file:///c:/Users/chait/Desktop/DPA_Project1/docs/asr_benchmark.md): ASR engine comparison (`faster-whisper`, `whisper.cpp`, `WhisperX`).

---

## 🗄️ Database Configuration

The pipeline supports both SQLite and PostgreSQL via SQLAlchemy:
* **Default (SQLite)**: Automatically initializes `earnings_call.db` in the repository root.
* **PostgreSQL**: Set `DATABASE_URL=postgresql://user:password@host:port/dbname` in `.env`.
* **Schema**:
  * `company_universe`: 25 curated US and Canadian public corporations.
  * `event_registry`: Discovered earnings dates, webcast URLs, and filing sources.
  * `crawl_log`: Discovery and capture crawler audit logs.

---

## ⚠️ Limitations & Methodological Disclosures

1. **Event Discovery Coverage**: 13 of 25 universe companies had active SEC EDGAR 8-K/10-Q earnings event dates available during crawling.
2. **Captured Audio Corpus**: 12 complete quarterly earnings calls (10 Microsoft, 2 Shopify) were captured and processed end-to-end.
3. **Shopify Reference Data**: Shopify does not publish written transcripts on its IR site; Canadian calls are marked N/A in WER and DER accuracy scoring to avoid unverified synthetic assumptions.
4. **Residual ASR Drop**: MSFT Q4 FY2025 has 1 residual ASR drop of 22.6s (597–620s, garbled speech during rapid sentence transition). All other 11 calls have 0 gaps >10s.
5. **Audio Files**: Audio WAV files (~4.2 GB) are managed locally and in `data/audio/capture_manifest.csv` and are gitignored to preserve repository compactness.
