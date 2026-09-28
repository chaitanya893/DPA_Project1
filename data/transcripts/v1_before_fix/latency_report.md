# Corporate Earnings Call Pipeline – Latency & RTF Report

**Measurement Date:** 2026-09-28 18:22:55 UTC  
**Compute Hardware:** `Intel64 Family 6 Model 186 Stepping 2, GenuineIntel` | **8 Cores** | **15.65 GB RAM** | Accelerator: `GPU (NVIDIA GeForce RTX 4050 Laptop GPU, 6.0 GB VRAM)`  
**Execution Environment:** Python 3.11 `.venv` | faster-whisper `small.en` (float16) | `pyannote/speaker-diarization-3.1` | PyTorch 2.5.1+cu121  
**Target SLA:** Publication of complete structured transcript within **5 minutes (300.0 seconds)** of call conclusion with zero queue overflow (`proc_time_sec < 60.0s`).  

**5-minute target: FAIL on 8-core CPU, PASS on RTX 4050 6 GB GPU (12/12 calls).**  

## 1. Measured 12-Call Latency & SLA Summary (12 Calls Measured)

| Ticker | Fiscal Period | Audio Duration | ASR Time | ASR RTF | Diarization Time | Diar RTF | Total RTF | Post-Call Latency | Queue Drained | Q&A Segments | 5-Min SLA |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SHOP** | Q2 FY2026 | 58.1 min | 206.3s | 0.0592 | 207.6s | 0.0596 | 0.1188 | 208.13s | YES | 311 | **PASS** |
| **SHOP** | Q1 FY2026 | 63.0 min | 334.0s | 0.0884 | 231.6s | 0.0613 | 0.1497 | 232.17s | YES | 355 | **PASS** |
| **MSFT** | Q4 FY2026 | 64.5 min | 174.0s | 0.0449 | 218.3s | 0.0564 | 0.1013 | 220.97s | YES | 312 | **PASS** |
| **MSFT** | Q3 FY2026 | 62.4 min | 215.8s | 0.0576 | 211.5s | 0.0565 | 0.1142 | 213.88s | YES | 354 | **PASS** |
| **MSFT** | Q2 FY2026 | 57.7 min | 207.9s | 0.0601 | 185.6s | 0.0536 | 0.1137 | 186.89s | YES | 251 | **PASS** |
| **MSFT** | Q1 FY2026 | 58.6 min | 109.3s | 0.0311 | 188.9s | 0.0537 | 0.0848 | 190.19s | YES | 296 | **PASS** |
| **MSFT** | Q4 FY2025 | 55.1 min | 104.0s | 0.0314 | 177.1s | 0.0535 | 0.0849 | 178.92s | YES | 253 | **PASS** |
| **MSFT** | Q3 FY2025 | 56.5 min | 143.5s | 0.0423 | 185.6s | 0.0547 | 0.0970 | 186.90s | YES | 297 | **PASS** |
| **MSFT** | Q2 FY2025 | 58.2 min | 111.3s | 0.0318 | 187.1s | 0.0536 | 0.0854 | 187.60s | YES | 354 | **PASS** |
| **MSFT** | Q1 FY2025 | 63.0 min | 115.5s | 0.0305 | 203.1s | 0.0537 | 0.0842 | 203.85s | YES | 276 | **PASS** |
| **MSFT** | Q3 FY2024 | 60.2 min | 114.4s | 0.0316 | 194.1s | 0.0537 | 0.0853 | 194.84s | YES | 325 | **PASS** |
| **MSFT** | Q2 FY2024 | 61.3 min | 131.2s | 0.0357 | 198.0s | 0.0539 | 0.0895 | 198.50s | YES | 303 | **PASS** |

## 2. Streaming Real-Time Factor (RTF) & Buffer Queue Analysis

- **Total Audio Ingested:** 43118.7s (11.98 hours) across 12 calls.
- **Total ASR Inference Time:** 1966.9s.
- **Measured ASR RTF:** Min = `0.0305`, Max = `0.0884`, Average = `0.0454`.
- **Per-Chunk Processing Time (60s chunks):** Min = `0.28s`, Max = `17.90s`, Mean = `2.58s`.
- **Buffer Queue Draining:** 12/12 calls maintained queue draining (`proc_time_sec < chunk_duration_sec`).
- **Measured Post-Call Latency:** Min = `178.92s`, Max = `232.17s`, Average = `200.24s`.
- **5-Minute SLA Compliance:** 12/12 calls satisfied post-call SLA (<= 300.0s).
- **Q&A Detection Integrity:** 100% of calls verified with active Q&A sections (`qa_segments > 0`).

## 3. Measured GPU Diarization Performance

- **Total GPU Diarization Time:** 2388.5s across all 12 calls.
- **Measured Diarization RTF on GPU:** Min = `0.0535`, Max = `0.0613`, Average = `0.0553`.
- **End-to-End Post-Call Latency:** Includes final chunk ASR inference + full pyannote diarization + speaker name resolution + section structuring + JSON publish.

## 4. CPU Baseline Measurements & Thread Experiment Analysis

### Measured Full-Call CPU Baseline (`SHOP_Q2_FY2026`, 58.1 min audio):
- **ASR Inference:** `1,314.6s` (21.9 min, ASR RTF: `0.3774`)
- **Queue Drained:** `false` (2 chunks exceeded 60.0s, max chunk `62.3s` > 60.0s)
- **Pyannote Diarization Time (estimate):** `~51.0 minutes` (based on measured 5-min RTF `0.8497`)
- **Post-Call Latency (estimate):** `~52.0 minutes` (exceeds 5.0 minute SLA deadline by >10x)
- **SLA Status:** `FAIL`

### Measured CPU Benchmarks on 5-Minute Clip (300.0s audio):
- **8 Physical Cores (Optimized):**
  - ASR Inference Time: `58.2s` (ASR RTF: `0.1940`)
  - Pyannote Diarization Time: `254.9s` (Diarization RTF: `0.8497`)
- **12 Logical Threads (Oversubscribed Hyperthreads):**
  - ASR Inference Time: `146.1s` (2.5x slowdown)
  - Pyannote Diarization Time: `558.9s` (2.2x slowdown due to OpenMP barrier thrashing on hybrid P/E cores)

In contrast, running on GPU (`GPU (NVIDIA GeForce RTX 4050 Laptop GPU, 6.0 GB VRAM)`) achieved an average ASR RTF of `0.0454` and Diarization RTF of `0.0553`, allowing all 12 calls to drain queues instantly and complete the entire end-to-end pipeline in **~178s – 232s**, fully satisfying the 5-minute SLA.
