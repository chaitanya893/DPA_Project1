# Read-Only Transcript Comparison Suite (Official IR vs. ASR Pipeline)

This folder contains the comparative alignment suite between official Microsoft Investor Relations written transcripts and our automated ASR transcription pipeline across all 10 captured Microsoft earnings calls.

---

## 1. Overview & Contents

- **`html/index.html`**: Master visual dashboard listing all 10 calls, error breakdown (Substitutions / Deletions / Insertions), normalized WER, non-operator WER, and financial entity recall.
- **`html/<CALL>.html`**: Self-contained, side-by-side interactive comparison pages for each individual call (`MSFT_Q2_FY2024.html` through `MSFT_Q4_FY2026.html`).
- **`COMPARISON_SUMMARY.md`**: Quantitative markdown summary table containing verified metrics.
- **`README.md`**: This guide.

---

## 2. How to Open and Inspect Locally

1. Open `docs/transcript_comparison/html/index.html` in any web browser:
   - On Windows: Double-click `docs/transcript_comparison/html/index.html` or run:
     ```powershell
     Start-Process "docs/transcript_comparison/html/index.html"
     ```
   - On macOS/Linux:
     ```bash
     open docs/transcript_comparison/html/index.html
     ```
2. Click **Inspect Diff ➔** on any quarterly call to view the interactive side-by-side comparison page.
3. Use the toggle buttons at the top of each page:
   - **`Normalised Aligned Diff (As Scored)`**: Word-level color-coded diff using `difflib.SequenceMatcher(autojunk=False)` on normalized text.
   - **`Raw Text Side-by-Side`**: Unnormalized official Microsoft reference transcript alongside our timestamped, speaker-attributed segment cards.

---

## 3. Colour Legend & Diff Interpretation

| Visual Style | Opcode / Category | Description |
| :--- | :--- | :--- |
| <span style="background: #ffebe9; color: #cf222e; border: 1px solid #ff8182; padding: 2px 6px; border-radius: 3px; font-weight: bold; text-decoration: line-through;">Red</span> | **Deletion** | Present in official reference transcript, missing in our ASR output. |
| <span style="background: #ddf4ff; color: #0969da; border: 1px solid #54aeff; padding: 2px 6px; border-radius: 3px; font-weight: bold;">Blue</span> | **Insertion** | Present only in our ASR transcript (e.g. operator remarks, vocal hesitations cleaned by editors). |
| <span style="background: #fff8c5; color: #9a6700; border: 1px solid #d4a72c; padding: 2px 6px; border-radius: 3px; font-weight: bold;">Orange</span> | **Substitution** | Word replacement (`reference → ours`), including phonetic variations and number formatting. |
| <span style="background: #f1f3f5; border-left: 4px solid #8c959f; padding: 2px 6px; border-radius: 3px;">Grey</span> | **Operator Segment** | Spoken operator teleconference greeting and queue directions (omitted from official IR publication). |

---

## 4. Why Differences Include Editorial Omissions (Not Just ASR Errors)

Microsoft's official Investor Relations written transcripts are lightly edited for investor dissemination:
- **Operator Omission**: The live teleconference operator's introduction, safe harbor advisory queue instructions, and participant introductions are omitted in written transcripts.
- **Cleaned Speech**: Minor vocal disfluencies (e.g. *um*, *uh*, false starts) are removed in written transcripts.
- **Measured Impact**: Removing operator segments reduces the measured WER from **7.62%** to **5.26%**, confirming that **2.36%** of the apparent error is due to editorial filtering in the ground-truth text rather than acoustic misrecognition.

---

## 5. Compliance & Licensing Notice

> [!IMPORTANT]
> The generated HTML files in `docs/transcript_comparison/html/` contain verbatim proprietary text from Microsoft's published transcripts.
> In accordance with project copyright and data compliance guidelines, **`docs/transcript_comparison/html/` is included in `.gitignore` and is kept strictly on the local machine**. Only summary metadata and scripts are version-controlled.

---

## 6. How to Regenerate

The entire suite can be reproduced deterministically with one command:
```bash
python scripts/build_comparison.py
```
This script re-computes all alignments, generates all HTML pages and summaries, and verifies that every metric matches `docs/accuracy_report.md` with 0 mismatches.
