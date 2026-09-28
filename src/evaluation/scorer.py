"""
Scoring and evaluation module for Phase 4 ASR accuracy benchmarking.
Computes Call-level WER/CER, Section WER (prepared remarks vs Q&A),
Count-Limited Entity Accuracy (6 categories), v1 vs v2 comparison,
and Word Error breakdown (substitutions, deletions, insertions via jiwer.process_words).
"""

import os
import sys
import json
import re
from typing import Dict, List, Tuple, Any
from collections import Counter
import jiwer

sys.path.insert(0, ".")
from src.evaluation.normalizer import normalize_text, raw_clean_text, strip_speaker_headers

# Known entity patterns and dictionaries for financial domain
ENTITY_PATTERNS = {
    "money": r"(?:\$\s*\d+(?:\.\d+)?\s*(?:billion|million|trillion|thousand|[bmk])\b|\$\s*\d+(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:billion|million|trillion)\s*dollars?\b)",
    "percentages": r"(?:\b\d+(?:\.\d+)?\s*%|\b\d+(?:\.\d+)?\s*percent\b|\b\d+\s*basis\s*points?\b|\b\d+\s*bps\b)",
    "dates_fiscal": r"(?:\b(?:Q[1-4]|FY\d{2,4}|fiscal\s+(?:year\s+)?\d{4})\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,?\s+\d{4})?)",
}

KEY_PEOPLE = [
    "Satya Nadella", "Amy Hood", "Jonathan Neilson", "Brett Iversen",
    "Alice Jolla", "Brian DeFoe", "Keith Weiss", "Karl Keirstead",
    "Brad Zelnick", "Kirk Materne", "Brent Thill", "Mark Moerdler",
    "Kash Rangan", "Raimo Lenschow", "Tyler Radke", "Alex Zukin",
    "Gregg Moskowitz", "Brad Sills", "Gabriela Borges", "Michael Turrin"
]

KEY_PRODUCTS_COMPANIES = [
    "Azure", "Copilot", "Windows", "Office 365", "Microsoft 365", "Teams",
    "Dynamics 365", "LinkedIn", "GitHub", "Xbox", "Fabric", "Foundry",
    "OpenAI", "Activision", "Nuance", "Morgan Stanley", "Goldman Sachs",
    "Barclays", "UBS", "JPMorgan", "Jefferies", "Citi", "Wells Fargo",
    "Bank of America", "Deutsche Bank", "Mizuho", "Wolfe Research",
    "Evercore", "Bernstein", "Guggenheim", "KeyBanc", "Macquarie",
    "Power BI", "Work IQ", "Agent 365", "Security Copilot", "GitHub Copilot"
]

KEY_TICKERS = ["MSFT", "SHOP", "ORCL", "AMZN", "GOOGL", "GOOG", "AAPL", "NVDA", "META"]


def split_reference_sections(ref_text: str) -> Tuple[str, str]:
    """Splits reference transcript into prepared remarks and Q&A portions."""
    qa_pattern = r"(?i)\n\s*(?:(?:with that,? )?(?:let\'s|we will|we\'ll)\s+(?:go|move)\s+to\s+q&a|.*?(?:move (?:over )?to (?:the )?q&a|open (?:the |up )?(?:call|line) for questions|first question|repeat (?:the |your )?instructions)|(?:QUESTIONS\s+AND\s+ANSWERS)|(?:Q&A\s*$))"
    m = re.search(qa_pattern, ref_text)
    if m:
        split_pos = m.start()
        prep_text = ref_text[:split_pos]
        qa_text = ref_text[split_pos:]
    else:
        lines = ref_text.split("\n")
        mid = int(len(lines) * 0.5)
        prep_text = "\n".join(lines[:mid])
        qa_text = "\n".join(lines[mid:])
    return prep_text, qa_text


def extract_entities_from_text(text_raw: str) -> Dict[str, List[str]]:
    """Extracts ground-truth entities across 6 categories from raw text."""
    entities = {
        "money": [],
        "percentages": [],
        "dates_fiscal": [],
        "person_names": [],
        "company_product": [],
        "tickers": [],
    }
    
    # 1. Regex patterns for money, percentages, dates
    for cat in ["money", "percentages", "dates_fiscal"]:
        pat = ENTITY_PATTERNS[cat]
        matches = re.findall(pat, text_raw, re.IGNORECASE)
        for m in matches:
            m_str = m.strip()
            if m_str and len(m_str) > 1:
                entities[cat].append(m_str)
                
    # 2. Key person names (full name only)
    for person in KEY_PEOPLE:
        cnt = len(re.findall(r"\b" + re.escape(person) + r"\b", text_raw, re.IGNORECASE))
        for _ in range(cnt):
            entities["person_names"].append(person)
            
    # 3. Product / Company names
    for prod in KEY_PRODUCTS_COMPANIES:
        cnt = len(re.findall(r"\b" + re.escape(prod) + r"\b", text_raw, re.IGNORECASE))
        for _ in range(cnt):
            entities["company_product"].append(prod)
            
    # 4. Tickers
    for ticker in KEY_TICKERS:
        cnt = len(re.findall(r"\b" + re.escape(ticker) + r"\b", text_raw))
        for _ in range(cnt):
            entities["tickers"].append(ticker)
            
    return entities


def evaluate_count_limited_entity_recall(ref_entities: Dict[str, List[str]], asr_norm: str) -> Dict[str, Dict[str, Any]]:
    """
    Computes count-limited entity matching:
    For each distinct normalized entity string, matched = min(count in reference, count in our normalized transcript).
    Person names match strictly as full names.
    """
    results = {}
    
    for cat, items in ref_entities.items():
        if not items:
            results[cat] = {"ref_count": 0, "matched_count": 0, "recall_pct": None}
            continue
            
        # Count frequencies in reference
        norm_ref_counts = Counter()
        for it in items:
            nit = normalize_text(it)
            if nit:
                norm_ref_counts[nit] += 1
                
        matched_total = 0
        ref_total = sum(norm_ref_counts.values())
        
        for norm_item, ref_freq in norm_ref_counts.items():
            # Count occurrences in asr_norm
            # For regex matching of exact normalized phrase
            escaped = re.escape(norm_item)
            asr_freq = len(re.findall(r"\b" + escaped + r"\b", asr_norm))
            matched_total += min(ref_freq, asr_freq)
            
        recall = (matched_total / ref_total * 100.0) if ref_total > 0 else None
        results[cat] = {
            "ref_count": ref_total,
            "matched_count": matched_total,
            "recall_pct": round(recall, 2) if recall is not None else None
        }
        
    return results


def run_full_accuracy_evaluation() -> Dict[str, Any]:
    """Runs complete Phase 4 Part A accuracy benchmarking with count-limited matching and word error process."""
    transcripts_dir = "data/transcripts"
    v1_transcripts_dir = "data/transcripts/v1_before_fix"
    reference_dir = "data/reference/transcripts"
    benchmark_out_dir = "data/benchmark/outputs"
    metrics_dir = "data/transcripts/metrics"
    
    msft_calls = [
        "MSFT_Q2_FY2024", "MSFT_Q3_FY2024", "MSFT_Q1_FY2025", "MSFT_Q2_FY2025",
        "MSFT_Q3_FY2025", "MSFT_Q4_FY2025", "MSFT_Q1_FY2026", "MSFT_Q2_FY2026",
        "MSFT_Q3_FY2026", "MSFT_Q4_FY2026"
    ]
    
    call_results = []
    section_results = []
    v1_v2_comparison = []
    word_error_details = []
    
    total_entities_all = {
        "percentages": {"ref_count": 0, "matched_count": 0},
        "company_product": {"ref_count": 0, "matched_count": 0},
        "money": {"ref_count": 0, "matched_count": 0},
        "dates_fiscal": {"ref_count": 0, "matched_count": 0},
        "person_names": {"ref_count": 0, "matched_count": 0},
        "tickers": {"ref_count": 0, "matched_count": 0},
    }
    
    for call_id in msft_calls:
        json_path = os.path.join(transcripts_dir, f"{call_id}.json")
        v1_json_path = os.path.join(v1_transcripts_dir, f"{call_id}.json")
        ref_path = os.path.join(reference_dir, f"{call_id}.txt")
        m_path = os.path.join(metrics_dir, f"{call_id}_metrics.json")
        
        if not os.path.exists(json_path) or not os.path.exists(ref_path):
            continue
            
        with open(json_path, "r", encoding="utf-8") as f:
            v2_json = json.load(f)
            
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_raw = f.read()
            
        v2_segs = v2_json.get("segments", [])
        v2_full_raw = " ".join(s.get("text", "") for s in v2_segs)
        duration_sec = v2_segs[-1].get("end", 0.0) if v2_segs else 0.0
        
        v2_full_norm = normalize_text(v2_full_raw)
        v2_full_clean = raw_clean_text(v2_full_raw)
        ref_full_norm = normalize_text(ref_raw, is_reference=True)
        ref_full_clean = raw_clean_text(ref_raw, is_reference=True)
        
        # Word Error Rates and Character Error Rates
        raw_wer = round(jiwer.wer(ref_full_clean, v2_full_clean) * 100.0, 2)
        raw_cer = round(jiwer.cer(ref_full_clean, v2_full_clean) * 100.0, 2)
        norm_wer = round(jiwer.wer(ref_full_norm, v2_full_norm) * 100.0, 2)
        norm_cer = round(jiwer.cer(ref_full_norm, v2_full_norm) * 100.0, 2)
        
        # Detailed word error analysis via jiwer.process_words
        word_proc = jiwer.process_words(ref_full_norm, v2_full_norm)
        subs = word_proc.substitutions
        dels = word_proc.deletions
        ins = word_proc.insertions
        hits = word_proc.hits
        ref_words_cnt = len(ref_full_norm.split())
        
        word_error_details.append({
            "call_id": call_id,
            "ref_words": ref_words_cnt,
            "hits": hits,
            "substitutions": subs,
            "deletions": dels,
            "insertions": ins,
            "wer_pct": f"{norm_wer:.2f}%"
        })
        
        call_results.append({
            "call_id": call_id,
            "duration": f"{int(duration_sec // 60)}m {int(duration_sec % 60):02d}s",
            "duration_sec": duration_sec,
            "raw_wer": raw_wer,
            "norm_wer": norm_wer,
            "raw_cer": raw_cer,
            "norm_cer": norm_cer,
        })
        
        # Section WER
        prep_segs = []
        qa_segs = []
        for sec in v2_json.get("sections", []):
            if sec.get("type") in ("operator_intro", "prepared_remarks"):
                prep_segs.extend(sec.get("segments", []))
            elif sec.get("type") == "qa":
                qa_segs.extend(sec.get("segments", []))
                
        asr_prep_raw = " ".join(s.get("text", "") for s in prep_segs)
        asr_qa_raw = " ".join(s.get("text", "") for s in qa_segs)
        ref_prep_raw, ref_qa_raw = split_reference_sections(ref_raw)
        
        asr_prep_norm = normalize_text(asr_prep_raw)
        ref_prep_norm = normalize_text(ref_prep_raw, is_reference=True)
        asr_qa_norm = normalize_text(asr_qa_raw)
        ref_qa_norm = normalize_text(ref_qa_raw, is_reference=True)
        
        prep_wer = round(jiwer.wer(ref_prep_norm, asr_prep_norm) * 100.0, 2) if ref_prep_norm else 0.0
        qa_wer = round(jiwer.wer(ref_qa_norm, asr_qa_norm) * 100.0, 2) if ref_qa_norm else 0.0
        delta = round(qa_wer - prep_wer, 2)
        
        section_results.append({
            "call_id": call_id,
            "prepared_remarks_wer": prep_wer,
            "qa_wer": qa_wer,
            "delta": delta,
        })
        
        # Count-Limited Entity Accuracy (v2)
        ref_entities = extract_entities_from_text(ref_raw)
        v2_entity_scores = evaluate_count_limited_entity_recall(ref_entities, v2_full_norm)
        for cat in total_entities_all:
            total_entities_all[cat]["ref_count"] += v2_entity_scores[cat]["ref_count"]
            total_entities_all[cat]["matched_count"] += v2_entity_scores[cat]["matched_count"]
            
        # v1 vs v2 Comparison
        v1_missing_sec = 0.0
        v1_norm_wer = 0.0
        v1_norm_cer = 0.0
        v1_entity_recall = 0.0
        
        if os.path.exists(v1_json_path):
            with open(v1_json_path, "r", encoding="utf-8") as fp:
                v1_json = json.load(fp)
            v1_segs = v1_json.get("segments", [])
            v1_full_raw = " ".join(s.get("text", "") for s in v1_segs)
            v1_full_norm = normalize_text(v1_full_raw)
            
            # v1 gaps
            v1_gaps = []
            for i in range(len(v1_segs) - 1):
                g = v1_segs[i+1]["start"] - v1_segs[i]["end"]
                if g > 10.0:
                    v1_gaps.append(g)
            v1_missing_sec = round(sum(v1_gaps), 1)
            v1_norm_wer = round(jiwer.wer(ref_full_norm, v1_full_norm) * 100.0, 2)
            v1_norm_cer = round(jiwer.cer(ref_full_norm, v1_full_norm) * 100.0, 2)
            
            v1_escores = evaluate_count_limited_entity_recall(ref_entities, v1_full_norm)
            v1_r_tot = sum(v1_escores[c]["ref_count"] for c in v1_escores if c != "tickers")
            v1_m_tot = sum(v1_escores[c]["matched_count"] for c in v1_escores if c != "tickers")
            v1_entity_recall = round(v1_m_tot / v1_r_tot * 100.0, 2) if v1_r_tot > 0 else 0.0

        # v2 gaps
        v2_gaps = []
        for i in range(len(v2_segs) - 1):
            g = v2_segs[i+1]["start"] - v2_segs[i]["end"]
            if g > 10.0:
                v2_gaps.append(g)
        v2_missing_sec = round(sum(v2_gaps), 1)
        
        v2_r_tot = sum(v2_entity_scores[c]["ref_count"] for c in v2_entity_scores if c != "tickers")
        v2_m_tot = sum(v2_entity_scores[c]["matched_count"] for c in v2_entity_scores if c != "tickers")
        v2_call_entity_recall = round(v2_m_tot / v2_r_tot * 100.0, 2) if v2_r_tot > 0 else 0.0
        
        v1_v2_comparison.append({
            "call_id": call_id,
            "v1_missing_sec": f"{v1_missing_sec:.1f}s",
            "v2_missing_sec": f"{v2_missing_sec:.1f}s",
            "v1_norm_wer": f"{v1_norm_wer:.2f}%",
            "v2_norm_wer": f"{norm_wer:.2f}%",
            "v1_norm_cer": f"{v1_norm_cer:.2f}%",
            "v2_norm_cer": f"{norm_cer:.2f}%",
            "v1_entity_recall": f"{v1_entity_recall:.2f}%",
            "v2_entity_recall": f"{v2_call_entity_recall:.2f}%",
        })

    # Summary of entity accuracy
    entity_summary = []
    total_ref_all = 0
    total_matched_all = 0
    for cat in ["percentages", "company_product", "money", "dates_fiscal", "person_names", "tickers"]:
        d = total_entities_all[cat]
        r = d["ref_count"]
        m = d["matched_count"]
        if r > 0:
            pct = round(m / r * 100.0, 2)
            entity_summary.append({
                "category": cat,
                "ref_count": r,
                "matched_count": m,
                "recall_pct": f"{pct:.2f}%"
            })
            total_ref_all += r
            total_matched_all += m
        else:
            entity_summary.append({
                "category": cat,
                "ref_count": 0,
                "matched_count": 0,
                "recall_pct": "N/A"
            })
        
    overall_recall = round(total_matched_all / total_ref_all * 100.0, 2) if total_ref_all > 0 else 100.0

    # 3-Library Benchmark Clip Accuracy
    with open(os.path.join(reference_dir, "MSFT_Q4_FY2026.txt"), "r", encoding="utf-8") as f:
        msft_ref_full = f.read()
    ref_lines = msft_ref_full.split("\n")
    msft_clip_ref_raw = "\n".join(ref_lines[:60])
    msft_clip_ref_norm = normalize_text(msft_clip_ref_raw, is_reference=True)
    
    benchmark_configs = [
        ("faster-whisper", "GPU (float16)", "MSFT_Q4_FY2026 (10m)", "faster_whisper_cuda_MSFT_Q4_FY2026.txt"),
        ("whisper.cpp", "GPU (CUDA)", "MSFT_Q4_FY2026 (10m)", "whisper_cpp_gpu_MSFT_Q4_FY2026.txt"),
        ("WhisperX", "GPU (float16 + align)", "MSFT_Q4_FY2026 (10m)", "whisperx_cuda_MSFT_Q4_FY2026.txt"),
        ("faster-whisper", "CPU (int8)", "MSFT_Q4_FY2026 (10m)", "faster_whisper_cpu_MSFT_Q4_FY2026.txt"),
        ("whisper.cpp", "CPU (ggml)", "MSFT_Q4_FY2026 (10m)", "whisper_cpp_cpu_MSFT_Q4_FY2026.txt"),
        ("faster-whisper", "CPU (int8)", "SHOP_Q2_FY2026 (10m)", "faster_whisper_cpu_SHOP_Q2_FY2026.txt"),
        ("faster-whisper", "GPU (float16)", "SHOP_Q2_FY2026 (10m)", "faster_whisper_cuda_SHOP_Q2_FY2026.txt"),
        ("whisper.cpp", "CPU (ggml)", "SHOP_Q2_FY2026 (10m)", "whisper_cpp_cpu_SHOP_Q2_FY2026.txt"),
        ("whisper.cpp", "GPU (CUDA)", "SHOP_Q2_FY2026 (10m)", "whisper_cpp_gpu_SHOP_Q2_FY2026.txt"),
        ("WhisperX", "GPU (float16 + align)", "SHOP_Q2_FY2026 (10m)", "whisperx_cuda_SHOP_Q2_FY2026.txt"),
    ]
    
    benchmark_results = []
    for lib, dev, clip_name, fname in benchmark_configs:
        fpath = os.path.join(benchmark_out_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            hyp_text = f.read()
            
        if "MSFT" in clip_name:
            hyp_norm = normalize_text(hyp_text)
            wer = round(jiwer.wer(msft_clip_ref_norm, hyp_norm) * 100.0, 2)
            cer = round(jiwer.cer(msft_clip_ref_norm, hyp_norm) * 100.0, 2)
            benchmark_results.append({
                "library": lib,
                "device": dev,
                "clip": clip_name,
                "wer_pct": f"{wer:.2f}%",
                "cer_pct": f"{cer:.2f}%",
            })
        else:
            benchmark_results.append({
                "library": lib,
                "device": dev,
                "clip": clip_name,
                "wer_pct": "N/A (no public ref)",
                "cer_pct": "N/A (no public ref)",
            })

    return {
        "call_results": call_results,
        "section_results": section_results,
        "entity_summary": entity_summary,
        "overall_recall": overall_recall,
        "v1_v2_comparison": v1_v2_comparison,
        "word_error_details": word_error_details,
        "benchmark_results": benchmark_results,
    }


if __name__ == "__main__":
    res = run_full_accuracy_evaluation()
    print("\n--- 1. CALL-LEVEL ACCURACY ---")
    for r in res["call_results"]:
        print(r)
    print("\n--- 2. SECTION ACCURACY ---")
    for r in res["section_results"]:
        print(r)
    print("\n--- 3. COUNT-LIMITED ENTITY ACCURACY ---")
    for r in res["entity_summary"]:
        print(r)
    print("Overall Recall:", res["overall_recall"], "%")
    print("\n--- 4. V1 VS V2 COMPARISON ---")
    for r in res["v1_v2_comparison"]:
        print(r)
    print("\n--- 5. WORD ERROR BREAKDOWN (SUBS / DELS / INS) ---")
    for r in res["word_error_details"]:
        print(r)
    print("\n--- 6. 3-LIBRARY BENCHMARK ACCURACY ---")
    for r in res["benchmark_results"]:
        print(r)
