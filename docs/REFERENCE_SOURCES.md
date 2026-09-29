# Reference Sources and Terms of Use

This document details the source origin, retrieval method, and licensing/terms conditions for reference transcripts used strictly for accuracy benchmarking and evaluation in Phase 4.

> [!NOTE]
> Reference transcripts are utilized **strictly offline for scoring and accuracy evaluation**. In compliance with data governance and copyright policies, reference text is never published to client databases, copied into public JSON deliverables, or redistributed.

---

## 1. Summary of Reference Sources

| Call Identifier | Publisher / Source | Direct Source URL / Origin | Status / Availability |
| :--- | :--- | :--- | :--- |
| **MSFT_Q2_FY2024** | Microsoft Investor Relations | `https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/TranscriptFY24Q2.docx` | Available (Official Word Transcript) |
| **MSFT_Q3_FY2024** | Microsoft Investor Relations | `https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/TranscriptFY24Q3.docx` | Available (Official Word Transcript) |
| **MSFT_Q4_FY2024** | Microsoft Investor Relations | `https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/TranscriptFY24Q4.docx` | Available (Official Word Transcript) |
| **MSFT_Q1_FY2025** | Microsoft Investor Relations | `https://aka.ms/transcriptfy25q1` (`TranscriptFY25Q1.docx`) | Available (Official Word Transcript) |
| **MSFT_Q2_FY2025** | Microsoft Investor Relations | `https://aka.ms/transcriptfy-25q2` (`TranscriptFY25Q2.docx`) | Available (Official Word Transcript) |
| **MSFT_Q3_FY2025** | Microsoft Investor Relations | `https://aka.ms/transcriptfy25q3` (`TranscriptFY25Q3.docx`) | Available (Official Word Transcript) |
| **MSFT_Q4_FY2025** | Microsoft Investor Relations | `https://aka.ms/transcriptfy25q4` (`TranscriptQandAFY25q4.docx`) | Available (Official Word Transcript) |
| **MSFT_Q1_FY2026** | Microsoft Investor Relations | `https://aka.ms/transcriptfy26q1` (`TranscriptFY26Q1.docx`) | Available (Official Word Transcript) |
| **MSFT_Q2_FY2026** | Microsoft Investor Relations | `https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/TranscriptQandAFY26q2.docx` | Available (Official Word Transcript) |
| **MSFT_Q3_FY2026** | Microsoft Investor Relations | `https://aka.ms/transcriptfy26q3` (`TranscriptFY26Q3.docx`) | Available (Official Word Transcript) |
| **MSFT_Q4_FY2026** | Microsoft Investor Relations | `https://aka.ms/transcriptfy26q4` (`TranscriptFY26Q4.docx`) | Available (Official Word Transcript) |
| **SHOP_Q1_FY2026** | Shopify Investor Relations | `https://investors.shopify.com` | **No public reference** (Shopify publishes webcasts & press releases only; no official written transcript) |
| **SHOP_Q2_FY2026** | Shopify Investor Relations | `https://investors.shopify.com` | **No public reference** (Shopify publishes webcasts & press releases only; no official written transcript) |

---

## 2. Licensing & Terms of Use Clauses

### Microsoft Corporation (Investor Relations)
- **Source**: Microsoft Corporation Investor Relations portal (`microsoft.com/investor`).
- **Access Method**: Direct document fetch respecting standard HTTP headers, rate limits (2–3s delay), and public access.
- **Terms Clause**: Materials on Microsoft Investor Relations are provided for informational and investor assessment purposes under standard Microsoft Terms of Use:
  > *"Microsoft grants permission to use Documents (such as white papers, press releases, datasheets and FAQs) from the Services, provided that (1) the below copyright notice appears in all copies and that both the copyright notice and this permission notice appear, (2) use of such Documents from the Services is for informational and non-commercial or personal use only and will not be copied or posted on any network computer or broadcast in any media, and (3) no modifications of any Documents are made."*
- **Compliance Action**: Transcripts are stored locally in plain text format (`data/reference/transcripts/`, which is gitignored) solely to compute objective benchmark error rates (WER, CER, Entity Recall).

### Shopify Inc. (Investor Relations & Third-Party Audit)
- **Official IR Status**: **No public reference**. Shopify does not distribute official verbatim text transcripts on its investor relations portal (`investors.shopify.com`), providing only press releases, financial tables, and webcast audio.
- **Third-Party Evaluation (The Motley Fool)**: Evaluated `fool.com` on 2026-09-29 as a potential source for third-party transcripts. While `robots.txt` does not explicitly disallow `/earnings/call-transcripts/`, The Motley Fool's Terms of Use (*The Motley Fool's Rules*, Section 7 Intellectual Property & Section 8 Conduct, updated January 29, 2026) strictly prohibit automated access:
  > *"You further agree not to create abstracts from or scrape our Content ... for use on another website or service"* (Section 7)
  > *"You may not use or allow others to use your Fool membership to: ... Use any automated means, including, without limitation, agents, robots, scripts, or spiders, to access, monitor, copy or harvest data from any part of our sites"* (Section 8)
- **Compliance Decision**: In strict compliance with target platform Terms of Service, automated fetching from `fool.com` was **not performed**. Shopify calls are scored as `N/A` in WER, CER, and DER ground-truth evaluations to preserve compliance integrity.
