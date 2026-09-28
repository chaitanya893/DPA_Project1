# Corporate Earnings Call Pipeline – Latency & RTF Report

**Measurement Date:** 2026-09-29 02:40:00 UTC  
**Compute Hardware:** `13th Gen Intel(R) Core(TM) i5-13450HX` | **8 Cores (Physical)** | **15.65 GB RAM** | Accelerator: `GPU (NVIDIA GeForce RTX 4050 Laptop GPU, 6.0 GB VRAM)`  
**Execution Environment:** Python 3.11 `.venv` | faster-whisper `small.en` (float16) | `pyannote/speaker-diarization-3.1` | PyTorch 2.5.1+cu121  
**Target SLA:** Publication of complete structured transcript within **5 minutes (300.0 seconds)** of call conclusion with zero queue overflow (`proc_time_sec < 60.0s`).  

**5-minute target: FAIL on 8-core CPU, PASS on RTX 4050 6 GB GPU (12/12 calls).**  

---

## 1. Measured 12-Call Latency & SLA Summary (12 Calls Measured)

| Ticker | Fiscal Period | Audio Duration | ASR Time | ASR RTF | Diarization Time | Diar RTF | Total RTF | Post-Call Latency | Queue Drained | Q&A Segments | 5-Min SLA |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SHOP** | Q2 FY2026 | 58.1 min | 115.2s | 0.0331 | 205.2s | 0.0589 | 0.0920 | 208.33s | YES | 306 | **PASS** |
| **SHOP** | Q1 FY2026 | 63.0 min | 95.8s | 0.0253 | 227.6s | 0.0602 | 0.0855 | 232.35s | YES | 334 | **PASS** |
| **MSFT** | Q4 FY2026 | 64.5 min | 156.8s | 0.0405 | 215.1s | 0.0556 | 0.0961 | 220.33s | YES | 252 | **PASS** |
| **MSFT** | Q3 FY2026 | 62.4 min | 127.1s | 0.0340 | 208.7s | 0.0558 | 0.0898 | 212.97s | YES | 266 | **PASS** |
| **MSFT** | Q2 FY2026 | 57.7 min | 118.8s | 0.0343 | 182.5s | 0.0527 | 0.0870 | 187.21s | YES | 224 | **PASS** |
| **MSFT** | Q1 FY2026 | 58.6 min | 119.5s | 0.0340 | 186.2s | 0.0530 | 0.0870 | 190.61s | YES | 274 | **PASS** |
| **MSFT** | Q4 FY2025 | 55.1 min | 113.6s | 0.0344 | 175.1s | 0.0530 | 0.0873 | 179.38s | YES | 219 | **PASS** |
| **MSFT** | Q3 FY2025 | 56.5 min | 111.4s | 0.0329 | 183.6s | 0.0542 | 0.0870 | 186.87s | YES | 227 | **PASS** |
| **MSFT** | Q2 FY2025 | 58.2 min | 119.8s | 0.0343 | 185.2s | 0.0530 | 0.0873 | 188.03s | YES | 249 | **PASS** |
| **MSFT** | Q1 FY2025 | 63.0 min | 134.4s | 0.0355 | 198.8s | 0.0526 | 0.0881 | 204.07s | YES | 258 | **PASS** |
| **MSFT** | Q3 FY2024 | 60.2 min | 133.5s | 0.0370 | 190.4s | 0.0527 | 0.0897 | 195.29s | YES | 256 | **PASS** |
| **MSFT** | Q2 FY2024 | 61.3 min | 116.1s | 0.0316 | 196.6s | 0.0535 | 0.0851 | 199.35s | YES | 260 | **PASS** |

---

## 2. Streaming Real-Time Factor (RTF) & Buffer Queue Analysis

- **Total Audio Ingested:** 43,267.3s (12.02 hours) across 12 calls.
- **Total ASR Inference Time:** 1,462.0s.
- **Measured ASR RTF on GPU:** Min = `0.0253`, Max = `0.0405`, Average = `0.0339`.
- **Per-Chunk Processing Time (60s chunks):** Min = `0.56s`, Max = `8.38s`, Mean = `2.37s`.
- **Buffer Queue Draining:** 12/12 calls maintained 100% queue draining (`proc_time_sec < 60.0s` for every single chunk).
- **Measured Post-Call Latency:** Min = `179.38s`, Max = `232.35s`, Average = `200.43s` (~3.34 minutes).
- **5-Minute SLA Compliance:** 12/12 calls satisfied the post-call SLA deadline ($\le 300.0\text{s}$).
- **Q&A Detection Integrity:** 100% of calls verified with active Q&A sections (`qa_segments > 0`).

---

## 3. Measured GPU Diarization Performance

- **Total GPU Diarization Time:** 2,355.0s across all 12 calls.
- **Measured Diarization RTF on GPU:** Min = `0.0526`, Max = `0.0602`, Average = `0.0548`.
- **End-to-End Post-Call Latency:** Includes final 60s chunk ASR inference + full pyannote diarization + speaker name resolution + section classification + publish.

---

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

In contrast, running on GPU (`NVIDIA GeForce RTX 4050 Laptop GPU`) achieved an average ASR RTF of `0.0339` and Diarization RTF of `0.0548`, allowing all 12 calls to drain queues instantly and complete the entire end-to-end pipeline in **~179s – 232s**, fully satisfying the 5-minute SLA.

---

## 5. Pipeline Architecture Evolution (v1 vs. v2 Overhaul)

### Root Cause of Dropped Speech & Boundary Duplication in v1:
1. **Initial Prompt Biasing:** In v1, passing `initial_prompt` on every 60s streaming chunk combined with default `condition_on_previous_text=True` caused CTranslate2/faster-whisper to periodically trigger prompt repetition suppression or decoder temperature fallbacks on challenging audio segments. This caused Whisper to emit truncation markers (`...`) and drop subsequent speech segments entirely (e.g. 573s–627s in `MSFT_Q4_FY2026`). Across the 10 MSFT calls, v1 exhibited 4–8 gaps >10s per call (88s–263s of audio dropped per call), inflating full-call WER to ~17%.
2. **Boundary Word Duplication:** Overlap word deduplication operating at segment text level duplicated phrases spanning chunk boundaries (~54 duplicates per call).

### Production Fixes Applied in v2:
1. **Prompt Sanitization & Context Decoupling:** Removed per-chunk `initial_prompt` and enforced `condition_on_previous_text=False` on primary streaming inference (`beam_size=1, vad_filter=True`).
2. **Exact Word-Level Boundary Slicing:** For chunk $k$ starting at $S_k$, words are sliced at $B = S_k + 1.5\text{s}$ (the exact midpoint of the 3.0s overlap), keeping words from chunk $k-1$ with $\text{start} < B$ and from chunk $k$ with $\text{start} \ge B$. This completely eliminated boundary phrase duplication across all calls (0 duplicate segments).
3. **Active Gap Detection & Safety Re-Pass:** After decoding each 60s chunk, the engine inspects segment boundaries. Any internal gap >5.0s (or following an ellipsis `...` truncation) is automatically re-transcribed with robust fallback (`beam_size=5, vad_filter=False`) and spliced strictly inside the gap window.
4. **Hallucination & Noise Suppression:** Dropped low-confidence segments (`no_speech_prob > 0.6 AND avg_logprob < -0.6`, or `avg_logprob < -1.2`) and known YouTube/speech artifacts (`"thanks for watching"`, `"subscribe"`), eliminating music hallucinations (9 segments dropped across the 12 calls).
5. **Residual Audio Gaps:** 11 out of 12 calls have 0 gaps >10s (0.0s missing audio). Exactly 1 residual ASR drop of 22.6s exists in `MSFT_Q4_FY2025` (597.3s–619.9s, where speech regarding deep reasoning agents was garbled and truncated).
6. **Latency & SLA Integrity:** All safety re-pass execution time is measured inside `proc_time_sec` for that chunk. The real measured max chunk time was **8.38s** (in `MSFT_Q2_FY2026`), remaining far below the 60.0s real-time streaming limit and ensuring 100% queue draining.
