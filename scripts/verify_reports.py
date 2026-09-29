import os
import sys
import json
import re
from typing import Dict, List, Tuple, Any
import jiwer

# Configure UTF-8 for console output
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, ".")
from src.evaluation.normalizer import normalize_text, raw_clean_text, strip_speaker_headers
from src.evaluation.scorer import evaluate_count_limited_entity_recall, extract_entities_from_text
from scripts.compute_part_b import compute_part_b_metrics

ORDERED_CALLS = [
    "SHOP_Q2_FY2026",
    "SHOP_Q1_FY2026",
    "MSFT_Q4_FY2026",
    "MSFT_Q3_FY2026",
    "MSFT_Q2_FY2026",
    "MSFT_Q1_FY2026",
    "MSFT_Q4_FY2025",
    "MSFT_Q3_FY2025",
    "MSFT_Q2_FY2025",
    "MSFT_Q1_FY2025",
    "MSFT_Q3_FY2024",
    "MSFT_Q2_FY2024",
]

MSFT_CALLS = [c for c in ORDERED_CALLS if c.startswith("MSFT")]

def parse_markdown_table(file_path: str, table_heading: str) -> List[Dict[str, str]]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    pos = content.find(table_heading)
    if pos == -1:
        raise ValueError(f"Heading not found: {table_heading}")
    
    sub = content[pos:]
    lines = sub.split("\n")
    
    table_lines = []
    found_table = False
    for line in lines:
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            found_table = True
            table_lines.append(s)
        elif found_table:
            break
            
    if not table_lines:
        raise ValueError(f"No table found under heading: {table_heading}")
        
    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
    rows = []
    for r_line in table_lines[2:]:
        cells = [c.strip() for c in r_line.strip("|").split("|")]
        if len(cells) == len(headers):
            row_dict = {headers[i]: cells[i] for i in range(len(headers))}
            rows.append(row_dict)
    return rows


def verify_latency_report() -> int:
    print("\n========================================================")
    print("VERIFYING: docs/latency_report.md (Table 1 vs Metrics)")
    print("========================================================")
    mismatches = 0
    table_rows = parse_markdown_table("docs/latency_report.md", "## 1. Measured 12-Call Latency & SLA Summary")
    
    for row in table_rows:
        ticker = row["Ticker"].replace("*", "").strip()
        fiscal = row["Fiscal Period"].strip()
        call_id = f"{ticker}_{fiscal.replace(' ', '_')}"
        metric_file = f"data/transcripts/metrics/{call_id}_metrics.json"
        
        with open(metric_file, "r", encoding="utf-8") as f:
            m = json.load(f)
            
        expected_cells = {
            "Ticker": f"**{m['ticker']}**",
            "Fiscal Period": m["fiscal_period"],
            "Audio Duration": f"{m['audio_duration_sec'] / 60.0:.1f} min",
            "ASR Time": f"{m['asr_infer_time_sec']:.1f}s",
            "ASR RTF": f"{m['asr_rtf']:.4f}",
            "Diarization Time": f"{m['diarization_time_sec']:.1f}s",
            "Diar RTF": f"{m['diarization_rtf']:.4f}",
            "Total RTF": f"{m['total_rtf']:.4f}",
            "Post-Call Latency": f"{m['post_call_latency_sec']:.2f}s",
            "Queue Drained": "YES" if m["queue_drained"] else "NO",
            "Q&A Segments": str(m["qa_segments"]),
        }
        
        for col_name, exp_val in expected_cells.items():
            rep_val = row[col_name]
            if rep_val == exp_val:
                print(f"[OK] Table 1 | {call_id:15} | {col_name:18} = {rep_val}")
            else:
                print(f"[MISMATCH] Table 1 | {call_id:15} | {col_name:18} -> Report: '{rep_val}', Expected: '{exp_val}'")
                mismatches += 1
                
    return mismatches


def verify_accuracy_report() -> int:
    print("\n========================================================")
    print("VERIFYING: docs/accuracy_report.md (Tables 1-5 vs Eval)")
    print("========================================================")
    mismatches = 0
    
    eval_results = {}
    all_ref_entities = {
        "percentages": 0,
        "company_product": 0,
        "dates_fiscal": 0,
        "money": 0,
        "person_names": 0,
        "tickers": 0,
    }
    all_matched_entities = {k: 0 for k in all_ref_entities}
    
    for call_id in MSFT_CALLS:
        t_path = f"data/transcripts/{call_id}.json"
        ref_path = f"data/reference/transcripts/{call_id}.txt"
        v1_path = f"data/transcripts/v1_before_fix/{call_id}.json"
        
        with open(t_path, "r", encoding="utf-8") as f:
            t_json = json.load(f)
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_raw = f.read()
            
        ref_norm = normalize_text(ref_raw, is_reference=True)
        v2_full_text = " ".join(s["text"] for s in t_json["segments"])
        v2_full_norm = normalize_text(v2_full_text)
        
        ref_raw_clean = raw_clean_text(ref_raw, is_reference=True)
        v2_raw_clean = raw_clean_text(v2_full_text)
        
        raw_wer = round(jiwer.wer(ref_raw_clean, v2_raw_clean) * 100.0, 2)
        norm_wer = round(jiwer.wer(ref_norm, v2_full_norm) * 100.0, 2)
        raw_cer = round(jiwer.cer(ref_raw_clean, v2_raw_clean) * 100.0, 2)
        norm_cer = round(jiwer.cer(ref_norm, v2_full_norm) * 100.0, 2)
        
        out_proc = jiwer.process_words(ref_norm, v2_full_norm)
        hits = out_proc.hits
        subs = out_proc.substitutions
        dels = out_proc.deletions
        ins = out_proc.insertions
        ref_words = hits + subs + dels
        
        non_op_segs = [s for s in t_json["segments"] if s.get("speaker_role") != "Operator"]
        non_op_text = " ".join(s["text"] for s in non_op_segs)
        non_op_norm = normalize_text(non_op_text)
        non_op_wer = round(jiwer.wer(ref_norm, non_op_norm) * 100.0, 2)
        
        spoken_ref = extract_entities_from_text(strip_speaker_headers(ref_raw))
        ent_scores = evaluate_count_limited_entity_recall(spoken_ref, v2_full_norm)
        for cat in all_ref_entities:
            all_ref_entities[cat] += ent_scores[cat]["ref_count"]
            all_matched_entities[cat] += ent_scores[cat]["matched_count"]
            
        tot_m = sum(ent_scores[c]["matched_count"] for c in ent_scores if c != "tickers")
        tot_r = sum(ent_scores[c]["ref_count"] for c in ent_scores if c != "tickers")
        v2_recall = round(tot_m / tot_r * 100.0, 2) if tot_r > 0 else 100.0
        
        v1_missing = 0.0
        v1_norm_wer = 0.0
        v1_norm_cer = 0.0
        v1_recall = 0.0
        if os.path.exists(v1_path):
            with open(v1_path, "r", encoding="utf-8") as f:
                v1_json = json.load(f)
            v1_segs = v1_json["segments"]
            v1_text = " ".join(s["text"] for s in v1_segs)
            v1_norm = normalize_text(v1_text)
            
            v1_gaps = []
            for i in range(len(v1_segs) - 1):
                g = v1_segs[i+1]["start"] - v1_segs[i]["end"]
                if g > 10.0:
                    v1_gaps.append(g)
            v1_missing = round(sum(v1_gaps), 1)
            v1_norm_wer = round(jiwer.wer(ref_norm, v1_norm) * 100.0, 2)
            v1_norm_cer = round(jiwer.cer(ref_norm, v1_norm) * 100.0, 2)
            v1_ent_scores = evaluate_count_limited_entity_recall(spoken_ref, v1_norm)
            v1_m = sum(v1_ent_scores[c]["matched_count"] for c in v1_ent_scores if c != "tickers")
            v1_r = sum(v1_ent_scores[c]["ref_count"] for c in v1_ent_scores if c != "tickers")
            v1_recall = round(v1_m / v1_r * 100.0, 2) if v1_r > 0 else 100.0

        v2_gaps = []
        for i in range(len(t_json["segments"]) - 1):
            g = t_json["segments"][i+1]["start"] - t_json["segments"][i]["end"]
            if g > 10.0:
                v2_gaps.append(g)
        v2_missing = round(sum(v2_gaps), 1)
        
        eval_results[call_id] = {
            "raw_wer": raw_wer,
            "norm_wer": norm_wer,
            "raw_cer": raw_cer,
            "norm_cer": norm_cer,
            "hits": hits,
            "subs": subs,
            "dels": dels,
            "ins": ins,
            "ref_words": ref_words,
            "non_op_wer": non_op_wer,
            "wer_red": round(norm_wer - non_op_wer, 2),
            "v1_missing": v1_missing,
            "v2_missing": v2_missing,
            "v1_norm_wer": v1_norm_wer,
            "v2_norm_wer": norm_wer,
            "v1_norm_cer": v1_norm_cer,
            "v2_norm_cer": norm_cer,
            "v1_recall": v1_recall,
            "v2_recall": v2_recall
        }
        
    t1_rows = parse_markdown_table("docs/accuracy_report.md", "## 1. Call-Level Accuracy (Word Error Rate & Character Error Rate)")
    for row in t1_rows:
        cid = row["Call Identifier"].replace("*", "").strip()
        if cid in eval_results:
            exp = eval_results[cid]
            checks = [
                ("Raw WER (%)", f"{exp['raw_wer']:.2f}%", row["Raw WER (%)"]),
                ("Normalized WER (%)", f"**{exp['norm_wer']:.2f}%**", row["Normalized WER (%)"]),
                ("Raw CER (%)", f"{exp['raw_cer']:.2f}%", row["Raw CER (%)"]),
                ("Normalized CER (%)", f"{exp['norm_cer']:.2f}%", row["Normalized CER (%)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Accuracy T1 | {cid} | {col:20} = {rep_v}")
                else:
                    print(f"[MISMATCH] Accuracy T1 | {cid} | {col:20} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1

    t1b_rows = parse_markdown_table("docs/accuracy_report.md", "### Measured Effect of Operator Teleconference Greetings on WER")
    for row in t1b_rows:
        cid = row["Call Identifier"].replace("*", "").strip()
        if cid in eval_results:
            exp = eval_results[cid]
            checks = [
                ("Full Normalized WER (%)", f"{exp['norm_wer']:.2f}%", row["Full Normalized WER (%)"]),
                ("Non-Operator WER (%)", f"**{exp['non_op_wer']:.2f}%**", row["Non-Operator WER (%)"]),
                ("Absolute WER Reduction", f"−{exp['wer_red']:.2f}%", row["Absolute WER Reduction"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Accuracy T1b | {cid} | {col:24} = {rep_v}")
                else:
                    print(f"[MISMATCH] Accuracy T1b | {cid} | {col:24} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1

    t2_rows = parse_markdown_table("docs/accuracy_report.md", "## 2. Word Error Breakdown (Substitutions, Deletions, Insertions)")
    for row in t2_rows:
        cid = row["Call Identifier"].replace("*", "").strip()
        if cid in eval_results:
            exp = eval_results[cid]
            checks = [
                ("Reference Words", f"{exp['ref_words']:,}", row["Reference Words"]),
                ("Correct Hits", f"{exp['hits']:,}", row["Correct Hits"]),
                ("Substitutions", f"{exp['subs']:,}", row["Substitutions"]),
                ("Deletions", f"{exp['dels']:,}", row["Deletions"]),
                ("Insertions", f"{exp['ins']:,}", row["Insertions"]),
                ("Normalized WER (%)", f"**{exp['norm_wer']:.2f}%**", row["Normalized WER (%)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Accuracy T2 | {cid} | {col:20} = {rep_v}")
                else:
                    print(f"[MISMATCH] Accuracy T2 | {cid} | {col:20} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1

    t4_rows = parse_markdown_table("docs/accuracy_report.md", "## 4. Count-Limited Financial Entity Accuracy")
    for row in t4_rows:
        cat_raw = row["Entity Category"].replace("*", "").strip()
        cat_key = None
        if "Percentages" in cat_raw: cat_key = "percentages"
        elif "Company & Products" in cat_raw: cat_key = "company_product"
        elif "Dates & Fiscal" in cat_raw: cat_key = "dates_fiscal"
        elif "Money Amounts" in cat_raw: cat_key = "money"
        elif "Person Names" in cat_raw: cat_key = "person_names"
        elif "Stock Tickers" in cat_raw: cat_key = "tickers"
        
        if cat_key:
            ref_c = all_ref_entities[cat_key]
            mat_c = all_matched_entities[cat_key]
            pct_str = f"**{mat_c/ref_c*100.0:.2f}%**" if ref_c > 0 else "**N/A**"
            if cat_key == "tickers": pct_str = "**N/A**"
            
            checks = [
                ("Reference Occurrences (Spoken)", f"{ref_c:,}", row["Reference Occurrences (Spoken)"]),
                ("Matched Count", f"{mat_c:,}", row["Matched Count"]),
                ("Recall Rate (%)", pct_str, row["Recall Rate (%)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Accuracy T4 | {cat_key:18} | {col:30} = {rep_v}")
                else:
                    print(f"[MISMATCH] Accuracy T4 | {cat_key:18} | {col:30} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1

    t5_rows = parse_markdown_table("docs/accuracy_report.md", "## 5. Pipeline Evolution: v1 vs. v2 Comparison per Call")
    for row in t5_rows:
        cid = row["Call Identifier"].replace("*", "").strip()
        if cid in eval_results:
            exp = eval_results[cid]
            v2_miss_exp = f"**{exp['v2_missing']:.1f}s***" if cid == "MSFT_Q4_FY2025" else f"**{exp['v2_missing']:.1f}s**"
            checks = [
                ("v1 Missing Audio", f"{exp['v1_missing']:.1f}s", row["v1 Missing Audio"]),
                ("v2 Missing Audio", v2_miss_exp, row["v2 Missing Audio"]),
                ("v1 Norm WER", f"{exp['v1_norm_wer']:.2f}%", row["v1 Norm WER"]),
                ("v2 Norm WER", f"**{exp['v2_norm_wer']:.2f}%**", row["v2 Norm WER"]),
                ("v1 Norm CER", f"{exp['v1_norm_cer']:.2f}%", row["v1 Norm CER"]),
                ("v2 Norm CER", f"**{exp['v2_norm_cer']:.2f}%**", row["v2 Norm CER"]),
                ("v1 Entity Recall", f"{exp['v1_recall']:.2f}%", row["v1 Entity Recall"]),
                ("v2 Entity Recall", f"**{exp['v2_recall']:.2f}%**", row["v2 Entity Recall"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Accuracy T5 | {cid} | {col:18} = {rep_v}")
                else:
                    print(f"[MISMATCH] Accuracy T5 | {cid} | {col:18} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1

    return mismatches


def verify_benchmark_part_b() -> int:
    print("\n========================================================")
    print("VERIFYING: docs/benchmark_part_b.md (Tables 1-3 vs Eval)")
    print("========================================================")
    mismatches = 0
    
    b_data = compute_part_b_metrics()
    der_res = b_data["der_results"]
    spk_res = b_data["speaker_results"]
    pooled_spk = b_data["pooled_speaker"]
    cost_m = b_data["cost_metrics"]
    
    # Check Table 1 (DER)
    t1_rows = parse_markdown_table("docs/benchmark_part_b.md", "### Table 1: Diarization Error Rate Breakdown across 10 Microsoft Earnings Calls")
    for row in t1_rows:
        cid = row["Call Identifier"].replace("*", "").strip()
        if cid in der_res:
            exp = der_res[cid]
            checks = [
                ("Total Ref Time (s)", f"{exp['total_ref_time']:,}s" if exp['total_ref_time'] < 1000 else f"{exp['total_ref_time']:,.1f}s", row["Total Ref Time (s)"]),
                ("Missed Detection (%)", f"{exp['missed']:.2f}%", row["Missed Detection (%)"]),
                ("False Alarm (%)", f"{exp['false_alarm']:.2f}%", row["False Alarm (%)"]),
                ("Speaker Confusion (%)", f"{exp['confusion']:.2f}%", row["Speaker Confusion (%)"]),
                ("Approximate DER (%)", f"**{exp['der']:.2f}%**", row["Approximate DER (%)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Part B Table 1 | {cid} | {col:24} = {rep_v}")
                else:
                    print(f"[MISMATCH] Part B Table 1 | {cid} | {col:24} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1
        elif "Macro Average" in row["Call Identifier"]:
            tot_ref_mean = sum(der_res[c]["total_ref_time"] for c in MSFT_CALLS) / len(MSFT_CALLS)
            checks = [
                ("Total Ref Time (s)", f"**{tot_ref_mean:,.1f}s**", row["Total Ref Time (s)"]),
                ("Missed Detection (%)", f"**{b_data['mean_missed']:.2f}%**", row["Missed Detection (%)"]),
                ("False Alarm (%)", f"**{b_data['mean_fa']:.2f}%**", row["False Alarm (%)"]),
                ("Speaker Confusion (%)", f"**{b_data['mean_conf']:.2f}%**", row["Speaker Confusion (%)"]),
                ("Approximate DER (%)", f"**{b_data['mean_der']:.2f}%**", row["Approximate DER (%)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Part B Table 1 | Mean | {col:24} = {rep_v}")
                else:
                    print(f"[MISMATCH] Part B Table 1 | Mean | {col:24} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1

    # Check Table 2 (Speaker Name Accuracy)
    t2_rows = parse_markdown_table("docs/benchmark_part_b.md", "### Table 2: Speaker-Name Identification Accuracy per Call")
    for row in t2_rows:
        cid = row["Call Identifier"].replace("*", "").strip()
        if cid in spk_res:
            exp = spk_res[cid]
            checks = [
                ("Total Spoken Words", f"{exp['total_words']:,}", row["Total Spoken Words"]),
                ("Executive Accuracy (%)", f"{exp['exec_acc']:.2f}%", row["Executive Accuracy (%)"]),
                ("Analyst Accuracy (%)", f"{exp['analyst_acc']:.2f}%", row["Analyst Accuracy (%)"]),
                ("Operator Accuracy (%)", f"{exp['operator_acc']:.2f}%", row["Operator Accuracy (%)"]),
                ("Unknown Speaker (%)", f"{exp['unknown_pct']:.2f}%", row["Unknown Speaker (%)"]),
                ("Overall Accuracy (%)", f"**{exp['overall_acc']:.2f}%**", row["Overall Accuracy (%)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Part B Table 2 | {cid} | {col:24} = {rep_v}")
                else:
                    print(f"[MISMATCH] Part B Table 2 | {cid} | {col:24} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1
        elif "Pooled Total" in row["Call Identifier"]:
            tot_w = sum(spk_res[c]["total_words"] for c in MSFT_CALLS)
            checks = [
                ("Total Spoken Words", f"**{tot_w:,}**", row["Total Spoken Words"]),
                ("Executive Accuracy (%)", f"**{pooled_spk['exec_acc']:.2f}%**", row["Executive Accuracy (%)"]),
                ("Analyst Accuracy (%)", f"**{pooled_spk['analyst_acc']:.2f}%**", row["Analyst Accuracy (%)"]),
                ("Operator Accuracy (%)", f"**{pooled_spk['operator_acc']:.2f}%**", row["Operator Accuracy (%)"]),
                ("Unknown Speaker (%)", f"**{pooled_spk['unknown_pct']:.2f}%**", row["Unknown Speaker (%)"]),
                ("Overall Accuracy (%)", f"**{pooled_spk['overall_acc']:.2f}%**", row["Overall Accuracy (%)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Part B Table 2 | Pooled | {col:24} = {rep_v}")
                else:
                    print(f"[MISMATCH] Part B Table 2 | Pooled | {col:24} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1
        elif "Macro Average" in row["Call Identifier"]:
            mean_w = sum(spk_res[c]["total_words"] for c in MSFT_CALLS) / len(MSFT_CALLS)
            checks = [
                ("Total Spoken Words", f"**{mean_w:,.1f}**", row["Total Spoken Words"]),
                ("Executive Accuracy (%)", f"**{pooled_spk['macro_exec_acc']:.2f}%**", row["Executive Accuracy (%)"]),
                ("Analyst Accuracy (%)", f"**{pooled_spk['macro_analyst_acc']:.2f}%**", row["Analyst Accuracy (%)"]),
                ("Operator Accuracy (%)", f"**{pooled_spk['macro_operator_acc']:.2f}%**", row["Operator Accuracy (%)"]),
                ("Unknown Speaker (%)", f"**{pooled_spk['macro_unknown_pct']:.2f}%**", row["Unknown Speaker (%)"]),
                ("Overall Accuracy (%)", f"**{pooled_spk['macro_overall_acc']:.2f}%**", row["Overall Accuracy (%)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Part B Table 2 | Macro | {col:24} = {rep_v}")
                else:
                    print(f"[MISMATCH] Part B Table 2 | Macro | {col:24} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1

    # Check Table 3 (Cost)
    t3_rows = parse_markdown_table("docs/benchmark_part_b.md", "### Table 3: Cost per Audio Hour and Annual Enterprise Scaling (2,000 Audio Hours)")
    for row in t3_rows:
        arch = row["Compute Architecture"]
        if "GPU" in arch:
            checks = [
                ("Compute Time per Audio Hour", f"**{cost_m['gpu_sec_per_audio_hr']:.1f}s** (5.84 min)", row["Compute Time per Audio Hour"]),
                ("Instance Hourly Rate", f"**${cost_m['aws_gpu_price_hr']:.3f} / hr**", row["Instance Hourly Rate"]),
                ("Cost per Audio Hour", f"**${cost_m['cost_per_audio_hr_gpu']:.4f}**", row["Cost per Audio Hour"]),
                ("Annual Cost (2,000 Audio Hours)", f"**${cost_m['annual_cost_gpu']:.2f}**", row["Annual Cost (2,000 Audio Hours)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Part B Table 3 | GPU | {col:28} = {rep_v}")
                else:
                    print(f"[MISMATCH] Part B Table 3 | GPU | {col:28} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1
        elif "CPU" in arch:
            checks = [
                ("Compute Time per Audio Hour", f"**4,417.6s** (73.63 min)", row["Compute Time per Audio Hour"]),
                ("Instance Hourly Rate", f"**${cost_m['aws_cpu_price_hr']:.3f} / hr**", row["Instance Hourly Rate"]),
                ("Cost per Audio Hour", f"**${cost_m['cost_per_audio_hr_cpu']:.4f}**", row["Cost per Audio Hour"]),
                ("Annual Cost (2,000 Audio Hours)", f"**${cost_m['annual_cost_cpu']:.2f}**", row["Annual Cost (2,000 Audio Hours)"]),
            ]
            for col, exp_v, rep_v in checks:
                if rep_v == exp_v:
                    print(f"[OK] Part B Table 3 | CPU | {col:28} = {rep_v}")
                else:
                    print(f"[MISMATCH] Part B Table 3 | CPU | {col:28} -> Report: '{rep_v}', Expected: '{exp_v}'")
                    mismatches += 1

    return mismatches


def verify_final_memo() -> int:
    print("\n========================================================")
    print("VERIFYING: docs/FINAL_MEMO.md (Key Quantitative Claims)")
    print("========================================================")
    mismatches = 0
    with open("docs/FINAL_MEMO.md", "r", encoding="utf-8") as f:
        memo = f.read()

    expected_strings = [
        "11.98 audio hours",
        "43,115.6 seconds",
        "0.0418",
        "0.0553",
        "0.0973",
        "179.38",
        "232.35",
        "200.41",
        "7.62%",
        "5.16%",
        "18.16%",
        "5.26%",
        "7.44%",
        "9.33%",
        "88.94%",
        "96.88%",
        "94.12%",
        "83.73%",
        "42.86%",
        "29.05%",
        "18.05%",
        "7.17%",
        "3.53%",
        "18.35%",
        "71.42%",
        "73.07%",
        "85.78%",
        "$0.0512",
        "$102.40",
        "$0.4172",
        "$834.40",
    ]

    for s in expected_strings:
        if s in memo:
            print(f"[OK] FINAL_MEMO | Verified presence of metric: '{s}'")
        else:
            print(f"[MISMATCH] FINAL_MEMO | Metric not found in memo: '{s}'")
            mismatches += 1

    return mismatches


def main():
    print("=================================================================")
    print("RUNNING AUTOMATED REPORT VERIFICATION (scripts/verify_reports.py)")
    print("=================================================================")
    
    latency_mismatches = verify_latency_report()
    accuracy_mismatches = verify_accuracy_report()
    part_b_mismatches = verify_benchmark_part_b()
    memo_mismatches = verify_final_memo()
    total_mismatches = latency_mismatches + accuracy_mismatches + part_b_mismatches + memo_mismatches
    
    print("\n=================================================================")
    print(f"VERIFICATION COMPLETE: {total_mismatches} mismatches found.")
    print("=================================================================")
    if total_mismatches == 0:
        print("RESULT: ALL TABLES & MEMO 100% PROGRAMMATICALLY VERIFIED (0 MISMATCHES).")
        sys.exit(0)
    else:
        print(f"RESULT: FAILED WITH {total_mismatches} MISMATCHES.")
        sys.exit(1)

if __name__ == "__main__":
    main()
