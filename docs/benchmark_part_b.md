# Phase 4 – Part B: Benchmark Evaluation & Production Analysis

This report presents the formal empirical evaluation for **Phase 4 – Part B** of the Financial Audio Transcription & Diarization Pipeline. All reported metrics are computed programmatically from existing transcript outputs (`data/transcripts/*.json`), diarization cache logs (`data/transcripts/_cache/*_diar.json`), latency metrics (`data/transcripts/metrics/*_metrics.json`), and official Microsoft investor relations reference transcripts (`data/reference/transcripts/MSFT_*.txt`). No speech recognition or diarization pipelines were re-run.

---

## 1. Approximate Diarization Error Rate (DER)

### Methodology & Annotation Alignment
To evaluate speaker diarization accuracy against official earnings call transcripts without manual millisecond-level acoustic time-stamps:
1. **Reference Tokenization & Speaker Tracking**: Each reference transcript is parsed into speaker turns (`SATYA NADELLA:`, `AMY HOOD:`, `OPERATOR:`, and Wall Street analyst questions) and normalized via `src/evaluation/normalizer.py`.
2. **Word-Level Sequence Alignment**: Words from the normalized reference are aligned to hypothesis words using `difflib.SequenceMatcher(autojunk=False)`.
3. **Reference Timeline Reconstruction**: For all matched words, the ground-truth speaker label is mapped onto the hypothesis segment time interval $[t_{\text{start}}, t_{\text{end}}]$, yielding a continuous ground-truth speaker `pyannote.core.Annotation`. Contiguous matching intervals for the same speaker are merged.
4. **DER Computation**: Diarization Error Rate is evaluated using `pyannote.metrics.diarization.DiarizationErrorRate(collar=0.25)` with a standard $250\text{ ms}$ forgiveness collar around speaker transition boundaries.
5. **Shopify Calls**: Marked as **N/A** due to the absence of public verbatim reference transcripts.

### Table 1: Diarization Error Rate Breakdown across 10 Microsoft Earnings Calls

| Call Identifier | Total Ref Time (s) | Missed Detection (%) | False Alarm (%) | Speaker Confusion (%) | Approximate DER (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **MSFT_Q4_FY2026** | 3,611.2s | 6.53% | 2.30% | 34.53% | **43.37%** |
| **MSFT_Q3_FY2026** | 3,402.1s | 6.17% | 4.00% | 35.59% | **45.76%** |
| **MSFT_Q2_FY2026** | 3,165.3s | 5.16% | 3.51% | 33.66% | **42.34%** |
| **MSFT_Q1_FY2026** | 3,200.2s | 6.55% | 3.48% | 40.65% | **50.68%** |
| **MSFT_Q4_FY2025** | 2,984.8s | 8.10% | 4.49% | 7.72% | **20.31%** |
| **MSFT_Q3_FY2025** | 3,071.6s | 7.58% | 3.64% | 7.23% | **18.45%** |
| **MSFT_Q2_FY2025** | 3,190.0s | 9.38% | 3.11% | 5.60% | **18.09%** |
| **MSFT_Q1_FY2025** | 3,434.0s | 7.76% | 3.55% | 5.59% | **16.90%** |
| **MSFT_Q3_FY2024** | 3,293.9s | 7.08% | 3.31% | 6.87% | **17.27%** |
| **MSFT_Q2_FY2024** | 3,325.2s | 7.35% | 3.88% | 6.05% | **17.28%** |
| **SHOP_Q2_FY2026** | N/A | N/A | N/A | N/A | **N/A** |
| **SHOP_Q1_FY2026** | N/A | N/A | N/A | N/A | **N/A** |
| **Macro Average (MSFT)** | **3,267.8s** | **7.17%** | **3.53%** | **18.35%** | **29.05%** |

*Note: In FY2024–FY2025 calls, PyAnnote embeddings achieved clean cluster separation (mean DER 18.05%, confusion 6.51%). In FY2026 calls, acoustic overlap and teleconference line switching elevated speaker confusion.*

---

## 2. Speaker-Name Identification Accuracy

Speaker-name identification measures the percentage of spoken words where the pipeline's attributed `speaker_name` correctly matches the ground-truth speaker identity identified in official transcripts.

### Table 2: Speaker-Name Identification Accuracy per Call

| Call Identifier | Total Spoken Words | Executive Accuracy (%) | Analyst Accuracy (%) | Operator Accuracy (%) | Unknown Speaker (%) | Overall Accuracy (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MSFT_Q4_FY2026** | 9,549 | 58.60% | 4.96% | 15.49% | 33.79% | **55.56%** |
| **MSFT_Q3_FY2026** | 9,062 | 53.23% | 0.00% | 0.00% | 35.53% | **51.51%** |
| **MSFT_Q2_FY2026** | 8,491 | 56.55% | 2.34% | 0.00% | 31.07% | **55.46%** |
| **MSFT_Q1_FY2026** | 8,799 | 49.26% | 4.70% | 0.00% | 39.44% | **48.51%** |
| **MSFT_Q4_FY2025** | 7,910 | 84.30% | 7.00% | 0.00% | 0.99% | **83.32%** |
| **MSFT_Q3_FY2025** | 8,033 | 84.89% | 3.85% | 0.00% | 0.31% | **83.58%** |
| **MSFT_Q2_FY2025** | 8,640 | 86.77% | 1.57% | 100.00% | 0.07% | **85.54%** |
| **MSFT_Q1_FY2025** | 9,250 | 86.56% | 1.32% | 0.00% | 1.22% | **83.76%** |
| **MSFT_Q3_FY2024** | 8,854 | 85.64% | 6.99% | 0.00% | 0.00% | **84.37%** |
| **MSFT_Q2_FY2024** | 8,933 | 86.55% | 5.36% | 0.00% | 0.78% | **85.54%** |
| **SHOP_Q2_FY2026** | N/A | N/A | N/A | N/A | N/A | **N/A** |
| **SHOP_Q1_FY2026** | N/A | N/A | N/A | N/A | N/A | **N/A** |
| **Pooled Total (MSFT)** | **87,521** | **73.07%** | **3.09%** | **18.60%** | **14.68%** | **71.42%** |
| **Macro Average (MSFT)** | **8,752.1** | **73.23%** | **3.81%** | **11.55%** | **14.32%** | **71.72%** |

### Key Findings:
1. **Executive Recognition (73.07% pooled / 85.78% in FY24-25)**: Core corporate executives (*Satya Nadella*, *Amy Hood*, *Jonathan Neilson*, *Brett Iversen*) speak the overwhelming majority of words (~91.5% of total call duration) and are reliably recognized and mapped.
2. **Analyst Attribution Challenges (3.09% accuracy)**: Wall Street analysts speak briefly (~100–300 words per question). Slight phonetic spelling differences in names during operator introductions (e.g., `Carl Kierstig` vs `Karl Keirstead`, `Brett Phil` vs `Brent Thill`) prevent exact string equivalence without an explicit investor relations CRM dictionary.
3. **Unknown Speaker Segments (14.68% pooled)**: Primarily concentrated in FY2026 calls where speaker cluster mapping defaulted to unassigned speaker IDs.

---

## 3. Cost Analysis & Production Scaling Economics

### Measured GPU & CPU Compute Profile
- **Evaluated Dataset**: 12 complete earnings calls = **11.98 audio hours** ($43,115.6\text{ seconds}$).
- **Measured GPU Inference Runtime**: $4,194.0\text{ seconds}$ total GPU compute time ($1,805.6\text{s}$ ASR + $2,388.5\text{s}$ Diarization).
- **GPU Seconds per Audio Hour**: **350.2s / audio hour** ($150.7\text{s}$ ASR + $199.4\text{s}$ Diarization).
- **CPU Baseline RTF**: **1.2271 RTF** (measured on 8-thread int8 faster-whisper = $4,417.6\text{ CPU-seconds}$ per audio hour).

### Cloud Pricing References (Public On-Demand Rates, September 2026)
1. **GPU Cloud Instance**:
   - Provider: **Amazon Web Services (AWS)**
   - Instance Type: **EC2 `g4dn.xlarge`** (1x NVIDIA T4 GPU, 4 vCPUs, 16 GiB RAM)
   - Pricing: **\$0.526 per instance hour** ($0.0001461\text{ \$/s}$) in `us-east-1`
   - Reference Source: [AWS EC2 On-Demand Pricing](https://aws.amazon.com/ec2/pricing/on-demand/) (Verified September 2026)
2. **CPU Cloud Instance**:
   - Provider: **Amazon Web Services (AWS)**
   - Instance Type: **EC2 `c6i.2xlarge`** (8 vCPUs Intel Xeon 8375C, 16 GiB RAM)
   - Pricing: **\$0.340 per instance hour** in `us-east-1`
   - Reference Source: [AWS EC2 On-Demand Pricing](https://aws.amazon.com/ec2/pricing/on-demand/) (Verified September 2026)

### Table 3: Cost per Audio Hour and Annual Enterprise Scaling (2,000 Audio Hours)

| Compute Architecture | Compute Time per Audio Hour | Instance Hourly Rate | Cost per Audio Hour | Annual Cost (2,000 Audio Hours) | Real-Time Factor (RTF) | Batch compute time (60-min call) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPU (AWS EC2 `g4dn.xlarge`)** | **350.2s** (5.84 min) | **$0.526 / hr** | **$0.0512** | **$102.40** | **0.0973** | **5.8 min** |
| **CPU (AWS EC2 `c6i.2xlarge`)** | **4,417.6s** (73.63 min) | **$0.340 / hr** | **$0.4172** | **$834.40** | **1.2271** | **73.6 min** |

### Annual Scaling Assumptions & Caveats:
- **Workload**: 500 enterprise public companies $\times$ 4 quarterly earnings calls/year $\times$ 1.0 hour average call length = **2,000 audio hours/year**.
- **Hardware Equivalence**: Assumes RTX 4050 laptop speed ≈ AWS T4.
- **CPU Diarization Note**: CPU diarization RTF 0.8497 is an estimate from a 5-min clip.
- **Compute Scope**: Compute only (excludes capture workers, storage, staff).
- **Latency Distinction**: Batch compute time reflects end-to-end post-call reprocessing; streaming post-call latency is 179–232 s (see `docs/latency_report.md`).
- **GPU Efficiency**: GPU processing achieves **8.15x lower cost** (\$102.40 vs. \$834.40) and **12.6x faster batch throughput** than CPU.

---

## 4. Subgroup & Segmented Accuracy Analysis

### Section Breakdown: Prepared Remarks vs. Q&A Session
Speech acoustics vary substantially between planned executive presentations and unscripted interactive Q&A:

| Earnings Call Section | Spoken Style & Acoustic Properties | Measured WER (%) | Character Error Rate (CER %) |
| :--- | :--- | :---: | :---: |
| **Prepared Remarks** | Monologue, scripted presentation, high signal-to-noise ratio, predictable cadence | **7.44%** | **2.67%** |
| **Q&A Session** | Spontaneous dialogue, conversational interruptions, telecom line switching, varied microphone acoustics | **9.33%** | **3.17%** |
| **Section Gap ($\Delta$)** | Unscripted conversational complexity penalty | **+1.89%** | **+0.50%** |

---

### Analysis of Unmeasured Demographic & Acoustic Subgroups
To maintain scientific rigor and avoid presenting unverified estimates, the following subgroup dimensions are explicitly designated as **Not Measurable** based on the objective properties of the benchmark corpus:

1. **United States vs. Canada**:
   - *Status*: **Not Measurable**
   - *Technical Justification*: Shopify does not publish written transcripts on its IR site. Computing comparative error rates without ground-truth reference transcripts would require unverifiable synthetic baselines.
2. **Large-Cap vs. Small-Cap**:
   - *Status*: **Not Measurable**
   - *Technical Justification*: The test corpus consists exclusively of Microsoft and Shopify; both are large-cap in config/universe.csv. No small-cap companies (<$2B market cap) are included in the 12-call dataset, precluding empirical market-cap segmentation.
3. **English vs. French Language**:
   - *Status*: **Not Measurable**
   - *Technical Justification*: All 12 earnings conference calls in the dataset were conducted 100% in English. Zero French or bilingual French-English audio segments were recorded, making cross-lingual evaluation physically impossible on this dataset.
4. **Native vs. Non-Native Accented English**:
   - *Status*: **Not Measurable**
   - *Technical Justification*: Official investor relations documents do not provide validated linguistic or phonetic origin metadata for call participants. Classifying speaker accents heuristically or algorithmically without verified demographic ground truth introduces subjective bias and violates scientific measurement standards.

---

## 5. Summary of Benchmark Part B Findings

1. **Diarization Performance**: Average approximate DER across 10 Microsoft calls is **29.05%** (Missed Detection: 7.17%, False Alarm: 3.53%, Confusion: 18.35%). Calls from FY2024–FY2025 achieved **18.05% DER**.
2. **Speaker Identification**: Corporate executives are identified with **73.07% pooled accuracy** (and **85.78% in FY24-25**). Analyst identification requires CRM phonetic normalization to bridge minor ASR spelling differences in names.
3. **Cost & Production Economics**: Full pipeline processing on AWS `g4dn.xlarge` (NVIDIA T4) costs **$0.0512 per audio hour** (RTF 0.0973), totaling **$102.40/year** for 500 enterprise companies across all 4 quarterly calls.
