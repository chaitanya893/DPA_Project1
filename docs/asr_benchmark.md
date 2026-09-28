# ASR Engine Comparative Benchmark Report

**Evaluation Scope:** First 10 minutes (600.0 seconds) of `MSFT_Q4_FY2026.wav` and `SHOP_Q2_FY2026.wav`  
**Model Architecture:** `small.en` across all evaluated libraries  
**Host Hardware:** `Intel64 Family 6 Model 186 Stepping 2, GenuineIntel` | 8 Physical Cores | 15.65 GB RAM | GPU: `NVIDIA GeForce RTX 4050 Laptop GPU (6.0 GB VRAM)`  
**Protocol:** Two passes per library/device combination; 1st run serves as warmup/caching, 2nd run is measured and reported.  
**VRAM Measurement Methodology:** Polled continuously via `nvidia-smi` query every 50–100ms during the active inference execution (Run 2). **Total Peak VRAM** is the primary GPU memory metric. The Net Delta VRAM column reflects active compute allocation above the idle baseline taken after initial model load.

---

## 1. Library Settings Matrix

| Library | Version / Framework | Beam Size | Batch Size | VAD Filter | Alignment Model | Compute Threads |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **faster-whisper** (CPU) | `1.1.1` / CTranslate2 `int8` | 1 | 1 | Off | None | 8 CPU threads |
| **faster-whisper** (GPU) | `1.1.1` / CTranslate2 `float16` | 1 | 1 | Off | None | 4 CPU threads (CUDA) |
| **whisper.cpp** (CPU) | `b5130` / GGML OpenMP | 5 | 1 | Off | None | 8 CPU threads |
| **whisper.cpp** (GPU) | `b5130` / GGML cuBLAS 12.4 | 5 | 1 | Off | None | 4 CPU threads (cuBLAS) |
| **WhisperX** (GPU) | `3.8.6` / PyTorch + CTranslate2 | 5 | 16 | pyannote VAD | wav2vec2_en (`whisperx.align`) | 4 CPU threads (CUDA) |

> [!NOTE]
> **Evaluation Settings Caveat:** Decoding parameters differ slightly across frameworks to match their native production configurations. `faster-whisper` uses `beam_size=1` (greedy decoding tuned for streaming throughput), whereas `whisper.cpp` and `WhisperX` default to `beam_size=5` (beam search).

---

## 2. Measured Benchmark Results

| Library / Framework | Device | Clip (10 min / 600s) | Wall Time (s) | Measured RTF | Peak RAM (MB) | Total Peak VRAM (MB) | Net VRAM Delta (MB)* | Text Output File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **faster-whisper** | CPU (int8) | `MSFT_Q4_FY2026` | 101.75s | 0.1696 | 810.5 MB | N/A | N/A | `data/benchmark/outputs/faster_whisper_cpu_MSFT_Q4_FY2026.txt` |
| **faster-whisper** | CPU (int8) | `SHOP_Q2_FY2026` | 104.05s | 0.1734 | 804.3 MB | N/A | N/A | `data/benchmark/outputs/faster_whisper_cpu_SHOP_Q2_FY2026.txt` |
| **faster-whisper** | GPU (float16) | `MSFT_Q4_FY2026` | 16.59s | 0.0277 | 734.7 MB | **739.0 MB** | 64.0 MB | `data/benchmark/outputs/faster_whisper_cuda_MSFT_Q4_FY2026.txt` |
| **faster-whisper** | GPU (float16) | `SHOP_Q2_FY2026` | 17.38s | 0.0290 | 734.6 MB | **739.0 MB** | 64.0 MB | `data/benchmark/outputs/faster_whisper_cuda_SHOP_Q2_FY2026.txt` |
| **whisper.cpp** | CPU (ggml) | `MSFT_Q4_FY2026` | 166.99s | 0.2783 | 927.7 MB | N/A | N/A | `data/benchmark/outputs/whisper_cpp_cpu_MSFT_Q4_FY2026.txt` |
| **whisper.cpp** | CPU (ggml) | `SHOP_Q2_FY2026` | 171.06s | 0.2851 | 924.5 MB | N/A | N/A | `data/benchmark/outputs/whisper_cpp_cpu_SHOP_Q2_FY2026.txt` |
| **whisper.cpp** | GPU (cuBLAS) | `MSFT_Q4_FY2026` | 27.57s | 0.0459 | 582.8 MB | **1606.0 MB** | 931.0 MB | `data/benchmark/outputs/whisper_cpp_gpu_MSFT_Q4_FY2026.txt` |
| **whisper.cpp** | GPU (cuBLAS) | `SHOP_Q2_FY2026` | 31.75s | 0.0529 | 585.4 MB | **1606.0 MB** | 931.0 MB | `data/benchmark/outputs/whisper_cpp_gpu_SHOP_Q2_FY2026.txt` |
| **WhisperX (ASR only)** | GPU (float16) | `MSFT_Q4_FY2026` | 6.93s | 0.0115 | 1495.6 MB | **3515.0 MB** | 1280.0 MB | — |
| **WhisperX (Alignment)** | GPU (float16) | `MSFT_Q4_FY2026` | 11.03s | 0.0184 | 1495.6 MB | **3515.0 MB** | 1280.0 MB | — |
| **WhisperX (Full pipeline)**| GPU (float16) | `MSFT_Q4_FY2026` | 17.96s | 0.0299 | 1495.6 MB | **3515.0 MB** | 1280.0 MB | `data/benchmark/outputs/whisperx_cuda_MSFT_Q4_FY2026.txt` |
| **WhisperX (ASR only)** | GPU (float16) | `SHOP_Q2_FY2026` | 7.14s | 0.0119 | 1508.1 MB | **3703.0 MB** | 1280.0 MB | — |
| **WhisperX (Alignment)** | GPU (float16) | `SHOP_Q2_FY2026` | 11.16s | 0.0186 | 1508.1 MB | **3703.0 MB** | 1280.0 MB | — |
| **WhisperX (Full pipeline)**| GPU (float16) | `SHOP_Q2_FY2026` | 18.31s | 0.0305 | 1508.1 MB | **3703.0 MB** | 1280.0 MB | `data/benchmark/outputs/whisperx_cuda_SHOP_Q2_FY2026.txt` |

*\*Net VRAM Delta is measured relative to idle VRAM after initial model weights are resident in GPU memory.*

---

## 3. Streaming vs. Batch Ingestion Architecture Note

- **Streaming Pipeline Engine (`faster-whisper`):** The production live earnings call ingestion pipeline processes audio in sequential 60-second rolling chunks with 3-second overlaps (`beam_size=1`, streaming generator). `faster-whisper` delivers consistent per-chunk latency (~1.8s–3.2s per 60s chunk on GPU), ensuring zero buffer queue overflow during real-time webcasts.
- **Batch Processing & Post-Call Re-Pass (`WhisperX`):** WhisperX achieves high initial ASR throughput (RTF ~0.011) by batching the entire file simultaneously (`batch_size=16`) after Pyannote VAD. When adding forced word-level alignment (`whisperx.align` with Wav2Vec2), execution time increases by +11.0s to a total of **~18.0s (RTF ~0.030)**. Because full-file batching requires the entire audio recording to be present upfront, `faster-whisper` remains the primary real-time streaming engine, while `WhisperX` serves as an ideal candidate for post-call re-passes and phoneme-level word timestamp alignment.
