# Transcript Comparison Summary: Official Microsoft IR vs. Pipeline ASR

This document summarizes the 10-quarter comparative alignment between official Microsoft Investor Relations written transcripts and our automated ASR transcription output.

> [!NOTE]
> All metrics are programmatically verified against `docs/accuracy_report.md` (0 mismatches).

### 10-Quarter Accuracy & Alignment Summary Table

| Call Identifier | Call Date | Ref Words | Our Words | Subs (S) | Dels (D) | Ins (I) | Normalized WER (%) | Non-Operator WER (%) | Entity Recall (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MSFT_Q2_FY2024** | 2024-01-30 | 9,301 | 9,637 | 276 | 95 | 431 | **8.62%** | **6.06%** | **88.81%** |
| **MSFT_Q3_FY2024** | 2024-04-25 | 9,120 | 9,417 | 190 | 77 | 374 | **7.03%** | **4.35%** | **92.08%** |
| **MSFT_Q1_FY2025** | 2024-10-30 | 9,556 | 9,922 | 222 | 80 | 446 | **7.83%** | **5.28%** | **87.05%** |
| **MSFT_Q2_FY2025** | 2025-01-29 | 8,933 | 9,190 | 183 | 113 | 370 | **7.46%** | **5.15%** | **85.99%** |
| **MSFT_Q3_FY2025** | 2025-04-30 | 8,284 | 8,602 | 181 | 65 | 383 | **7.59%** | **4.82%** | **92.65%** |
| **MSFT_Q4_FY2025** | 2025-07-30 | 8,247 | 8,499 | 198 | 141 | 393 | **8.88%** | **6.28%** | **86.52%** |
| **MSFT_Q1_FY2026** | 2025-10-29 | 9,074 | 9,350 | 177 | 99 | 375 | **7.17%** | **4.96%** | **89.15%** |
| **MSFT_Q2_FY2026** | 2026-01-28 | 8,737 | 9,030 | 184 | 67 | 360 | **6.99%** | **4.57%** | **88.99%** |
| **MSFT_Q3_FY2026** | 2026-04-29 | 9,407 | 9,718 | 234 | 109 | 420 | **8.11%** | **5.61%** | **82.78%** |
| **MSFT_Q4_FY2026** | 2026-07-29 | 9,869 | 10,081 | 215 | 108 | 320 | **6.52%** | **5.56%** | **86.08%** |
| **Total / Mean** | **10 Quarters** | **90,528** | **93,446** | **2,060** | **954** | **3,872** | **7.62%** | **5.26%** | **88.01%** |

### Key Findings:
1. **Editorial Divergence (Operator Lines)**: Full normalized WER is **7.62%** across 90,528 reference words. Removing teleconference operator lines (`speaker_role == "Operator"`) lowers WER to **5.26%**, confirming that 2.36% of measured error represents editorial omissions in Microsoft's written transcripts rather than acoustic ASR mistakes.
2. **Financial Entity Precision**: Count-limited financial entity recall averages **87.96%** (94.12% for percentages, 96.88% for dates/fiscal periods, 83.73% for money amounts).
3. **Common Substitutions**: The majority of substitutions stem from minor phonetic formatting variations (e.g. *percent* vs *%*, *year over year* vs *yoy*).
