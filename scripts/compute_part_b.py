import os
import sys
import json
import re
import difflib
from typing import Dict, List, Tuple, Any

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pyannote.metrics
from pyannote.metrics.diarization import DiarizationErrorRate
from pyannote.core import Segment, Annotation

sys.path.insert(0, ".")
from src.evaluation.normalizer import normalize_text, strip_speaker_headers

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

def parse_reference_speakers(ref_raw: str) -> List[Tuple[str, str]]:
    speaker_pattern = re.compile(r"^[ \t]*([A-Z0-9\s\.\,\'\-\&]+?):[ \t]*(.*)$", re.MULTILINE)
    matches = list(speaker_pattern.finditer(ref_raw))
    if not matches:
        return [("UNKNOWN", ref_raw)]
        
    blocks = []
    for i, m in enumerate(matches):
        raw_spk = m.group(1).strip()
        spk_clean = raw_spk.split(",")[0].strip()
        spk_clean = re.sub(r"\s+", " ", spk_clean)
        start_pos = m.end()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(ref_raw)
        
        inline_text = m.group(2)
        rest_text = ref_raw[start_pos:end_pos]
        full_block = (inline_text + "\n" + rest_text).strip()
        full_block = re.sub(r"\([^\)]*\)", " ", full_block)
        full_block = re.sub(r"\[[^\]]*\]", " ", full_block)
        
        if full_block:
            blocks.append((spk_clean, full_block))
            
    return blocks

def compute_part_b_metrics() -> Dict[str, Any]:
    der_results = {}
    speaker_results = {}
    
    # 1. Evaluate 10 MSFT calls
    for call_id in MSFT_CALLS:
        ref_path = f"data/reference/transcripts/{call_id}.txt"
        hyp_path = f"data/transcripts/{call_id}.json"
        diar_path = f"data/transcripts/_cache/{call_id}_diar.json"
        
        try:
            with open(ref_path, "r", encoding="utf-8") as f:
                ref_raw = f.read()
            with open(hyp_path, "r", encoding="utf-8") as f:
                hyp_json = json.load(f)
            with open(diar_path, "r", encoding="utf-8") as f:
                diar_json = json.load(f)
                
            # Parse reference tokens
            ref_blocks = parse_reference_speakers(ref_raw)
            ref_tokens = []
            for spk, text in ref_blocks:
                norm_t = normalize_text(text)
                words = norm_t.split()
                for w in words:
                    ref_tokens.append((w, spk))
                    
            # Parse hypothesis tokens
            hyp_tokens = []
            for seg in hyp_json["segments"]:
                norm_t = normalize_text(seg["text"])
                words = norm_t.split()
                if not words:
                    continue
                seg_dur = max(seg["end"] - seg["start"], 0.01)
                w_step = seg_dur / len(words)
                for idx, w in enumerate(words):
                    w_start = seg["start"] + idx * w_step
                    w_end = seg["start"] + (idx + 1) * w_step
                    hyp_tokens.append({
                        "word": w,
                        "start": w_start,
                        "end": w_end,
                        "speaker_id": seg.get("speaker_id", "UNKNOWN"),
                        "speaker_name": seg.get("speaker_name") or "Unknown",
                        "speaker_role": seg.get("speaker_role") or "Unknown",
                    })
                    
            # Match words via SequenceMatcher
            ref_words_only = [t[0] for t in ref_tokens]
            hyp_words_only = [t["word"] for t in hyp_tokens]
            sm = difflib.SequenceMatcher(None, ref_words_only, hyp_words_only, autojunk=False)
            matches = sm.get_matching_blocks()
            
            ref_annotation = Annotation(uri=call_id)
            aligned_matches = []
            
            current_spk = None
            cur_start = None
            cur_end = None
            
            for mb in matches:
                for k in range(mb.size):
                    r_idx = mb.a + k
                    h_idx = mb.b + k
                    r_spk = ref_tokens[r_idx][1]
                    h_tok = hyp_tokens[h_idx]
                    
                    aligned_matches.append((r_spk, h_tok))
                    
                    if r_spk == current_spk and cur_end is not None and abs(h_tok["start"] - cur_end) < 1.0:
                        cur_end = h_tok["end"]
                    else:
                        if current_spk is not None:
                            ref_annotation[Segment(cur_start, cur_end)] = current_spk
                        current_spk = r_spk
                        cur_start = h_tok["start"]
                        cur_end = h_tok["end"]
                        
            if current_spk is not None:
                ref_annotation[Segment(cur_start, cur_end)] = current_spk
                
            # Build hypothesis annotation from diarization turns
            hyp_annotation = Annotation(uri=call_id)
            diar_turns = diar_json.get("diar_segments", diar_json if isinstance(diar_json, list) else [])
            for turn in diar_turns:
                if turn["end"] > turn["start"]:
                    hyp_annotation[Segment(turn["start"], turn["end"])] = turn["speaker_id"]
                    
            der_metric = DiarizationErrorRate(collar=0.25)
            der_res = der_metric(ref_annotation, hyp_annotation, detailed=True)
            
            total_time = der_res["total"]
            der_pct = round(der_res["diarization error rate"] * 100.0, 2)
            miss_pct = round((der_res["missed detection"] / total_time * 100.0), 2) if total_time > 0 else 0.0
            fa_pct = round((der_res["false alarm"] / total_time * 100.0), 2) if total_time > 0 else 0.0
            conf_pct = round((der_res["confusion"] / total_time * 100.0), 2) if total_time > 0 else 0.0
            
            der_results[call_id] = {
                "der": der_pct,
                "missed": miss_pct,
                "false_alarm": fa_pct,
                "confusion": conf_pct,
                "total_ref_time": round(total_time, 2)
            }
            
            # Speaker name accuracy
            total_aligned = len(aligned_matches)
            name_correct = 0
            unknown_count = 0
            exec_total, exec_corr = 0, 0
            analyst_total, analyst_corr = 0, 0
            op_total, op_corr = 0, 0
            
            for r_spk, h_tok in aligned_matches:
                h_name = h_tok["speaker_name"]
                
                if h_name in ["Unknown", "UNKNOWN", ""]:
                    unknown_count += 1
                    
                is_match = (r_spk.strip().lower() == h_name.strip().lower())
                if not is_match and ("operator" in r_spk.lower() and "operator" in h_name.lower()):
                    is_match = True
                if is_match:
                    name_correct += 1
                    
                if r_spk in ["SATYA NADELLA", "AMY HOOD", "JONATHAN NEILSON", "BRETT IVERSEN"]:
                    exec_total += 1
                    if is_match: exec_corr += 1
                elif "OPERATOR" in r_spk:
                    op_total += 1
                    if is_match: op_corr += 1
                else:
                    analyst_total += 1
                    if is_match: analyst_corr += 1
                    
            speaker_results[call_id] = {
                "total_words": total_aligned,
                "overall_acc": round((name_correct / total_aligned * 100.0), 2) if total_aligned else 0.0,
                "exec_acc": round((exec_corr / exec_total * 100.0), 2) if exec_total else 0.0,
                "analyst_acc": round((analyst_corr / analyst_total * 100.0), 2) if analyst_total else 0.0,
                "operator_acc": round((op_corr / op_total * 100.0), 2) if op_total else 0.0,
                "unknown_pct": round((unknown_count / total_aligned * 100.0), 2) if total_aligned else 0.0,
                "exec_counts": (exec_corr, exec_total),
                "analyst_counts": (analyst_corr, analyst_total),
                "op_counts": (op_corr, op_total),
                "total_counts": (name_correct, total_aligned),
                "unknown_counts": (unknown_count, total_aligned)
            }
        except Exception as e:
            print(f"Error evaluating {call_id}: {e}")
            der_results[call_id] = {"der": 0.0, "missed": 0.0, "false_alarm": 0.0, "confusion": 0.0, "error": str(e)}
            speaker_results[call_id] = {"overall_acc": 0.0, "exec_acc": 0.0, "analyst_acc": 0.0, "operator_acc": 0.0, "unknown_pct": 0.0, "error": str(e)}

    # Means
    mean_der = round(sum(der_results[c]["der"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2)
    mean_missed = round(sum(der_results[c]["missed"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2)
    mean_fa = round(sum(der_results[c]["false_alarm"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2)
    mean_conf = round(sum(der_results[c]["confusion"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2)
    
    # Overall pooled speaker name accuracy
    tot_words = sum(speaker_results[c]["total_counts"][1] for c in MSFT_CALLS)
    tot_corr = sum(speaker_results[c]["total_counts"][0] for c in MSFT_CALLS)
    tot_exec = sum(speaker_results[c]["exec_counts"][1] for c in MSFT_CALLS)
    tot_exec_corr = sum(speaker_results[c]["exec_counts"][0] for c in MSFT_CALLS)
    tot_analyst = sum(speaker_results[c]["analyst_counts"][1] for c in MSFT_CALLS)
    tot_analyst_corr = sum(speaker_results[c]["analyst_counts"][0] for c in MSFT_CALLS)
    tot_op = sum(speaker_results[c]["op_counts"][1] for c in MSFT_CALLS)
    tot_op_corr = sum(speaker_results[c]["op_counts"][0] for c in MSFT_CALLS)
    tot_unk = sum(speaker_results[c]["unknown_counts"][0] for c in MSFT_CALLS)
    
    pooled_speaker = {
        "overall_acc": round(tot_corr / tot_words * 100.0, 2),
        "exec_acc": round(tot_exec_corr / tot_exec * 100.0, 2),
        "analyst_acc": round(tot_analyst_corr / tot_analyst * 100.0, 2),
        "operator_acc": round(tot_op_corr / tot_op * 100.0, 2),
        "unknown_pct": round(tot_unk / tot_words * 100.0, 2),
        "macro_overall_acc": round(sum(speaker_results[c]["overall_acc"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2),
        "macro_exec_acc": round(sum(speaker_results[c]["exec_acc"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2),
        "macro_analyst_acc": round(sum(speaker_results[c]["analyst_acc"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2),
        "macro_operator_acc": round(sum(speaker_results[c]["operator_acc"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2),
        "macro_unknown_pct": round(sum(speaker_results[c]["unknown_pct"] for c in MSFT_CALLS) / len(MSFT_CALLS), 2),
    }
    
    # 2. Compute cost metrics across all 12 calls
    total_audio_sec = 0.0
    total_asr_gpu_sec = 0.0
    total_diar_gpu_sec = 0.0
    
    for call_id in ORDERED_CALLS:
        metric_file = f"data/transcripts/metrics/{call_id}_metrics.json"
        with open(metric_file, "r", encoding="utf-8") as f:
            m = json.load(f)
        total_audio_sec += m["audio_duration_sec"]
        total_asr_gpu_sec += m["asr_infer_time_sec"]
        total_diar_gpu_sec += m["diarization_time_sec"]
        
    total_audio_hrs = total_audio_sec / 3600.0
    total_pipeline_gpu_sec = total_asr_gpu_sec + total_diar_gpu_sec
    
    gpu_sec_per_audio_hr = round(total_pipeline_gpu_sec / total_audio_hrs, 1)
    asr_sec_per_audio_hr = round(total_asr_gpu_sec / total_audio_hrs, 1)
    diar_sec_per_audio_hr = round(total_diar_gpu_sec / total_audio_hrs, 1)
    
    # AWS EC2 g4dn.xlarge (1x NVIDIA T4 GPU) = $0.526/hr
    aws_gpu_hr_price = 0.526
    # Compute time in hours per audio hour
    gpu_compute_hr_per_audio_hr = gpu_sec_per_audio_hr / 3600.0
    cost_per_audio_hr_gpu = round(gpu_compute_hr_per_audio_hr * aws_gpu_hr_price, 4)
    
    # CPU baseline: RTF = 1.2271 (from benchmark 8-thread int8 faster-whisper)
    # 1 audio hour = 3600s * 1.2271 = 4417.56 CPU-seconds
    # On AWS c6i.2xlarge (8 vCPUs) = $0.340/hr
    aws_cpu_hr_price = 0.340
    cpu_compute_hr_per_audio_hr = 1.2271 # RTF is ratio of compute time to audio duration
    cost_per_audio_hr_cpu = round(cpu_compute_hr_per_audio_hr * aws_cpu_hr_price, 4)
    
    # 500 companies * 4 calls/yr * 1.0 hr = 2,000 audio hours
    annual_audio_hrs = 2000.0
    annual_cost_gpu = round(annual_audio_hrs * cost_per_audio_hr_gpu, 2)
    annual_cost_cpu = round(annual_audio_hrs * cost_per_audio_hr_cpu, 2)
    
    return {
        "der_results": der_results,
        "mean_der": mean_der,
        "mean_missed": mean_missed,
        "mean_fa": mean_fa,
        "mean_conf": mean_conf,
        "speaker_results": speaker_results,
        "pooled_speaker": pooled_speaker,
        "cost_metrics": {
            "total_audio_hrs": round(total_audio_hrs, 2),
            "total_asr_gpu_sec": round(total_asr_gpu_sec, 1),
            "total_diar_gpu_sec": round(total_diar_gpu_sec, 1),
            "total_pipeline_gpu_sec": round(total_pipeline_gpu_sec, 1),
            "gpu_sec_per_audio_hr": gpu_sec_per_audio_hr,
            "asr_sec_per_audio_hr": asr_sec_per_audio_hr,
            "diar_sec_per_audio_hr": diar_sec_per_audio_hr,
            "cost_per_audio_hr_gpu": cost_per_audio_hr_gpu,
            "cost_per_audio_hr_cpu": cost_per_audio_hr_cpu,
            "annual_audio_hrs": annual_audio_hrs,
            "annual_cost_gpu": annual_cost_gpu,
            "annual_cost_cpu": annual_cost_cpu,
            "aws_gpu_instance": "AWS EC2 g4dn.xlarge (1x NVIDIA T4, 4 vCPUs, 16 GiB RAM)",
            "aws_gpu_price_hr": aws_gpu_hr_price,
            "aws_cpu_instance": "AWS EC2 c6i.2xlarge (8 vCPUs, 16 GiB RAM)",
            "aws_cpu_price_hr": aws_cpu_hr_price,
        }
    }

if __name__ == "__main__":
    results = compute_part_b_metrics()
    print(json.dumps(results, indent=2))
