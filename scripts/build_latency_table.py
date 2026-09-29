import json
import os
import glob
from typing import List, Dict, Any

METRICS_DIR = "data/transcripts/metrics"

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

def load_metrics() -> List[Dict[str, Any]]:
    results = []
    for call_id in ORDERED_CALLS:
        path = os.path.join(METRICS_DIR, f"{call_id}_metrics.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing metrics file: {path}")
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
            d["call_id"] = call_id
            results.append(d)
    return results

def generate_table_and_stats():
    metrics = load_metrics()
    
    total_audio_sec = sum(m["audio_duration_sec"] for m in metrics)
    total_asr_sec = sum(m["asr_infer_time_sec"] for m in metrics)
    total_diar_sec = sum(m["diarization_time_sec"] for m in metrics)
    
    asr_rtfs = [m["asr_rtf"] for m in metrics]
    diar_rtfs = [m["diarization_rtf"] for m in metrics]
    total_rtfs = [m["total_rtf"] for m in metrics]
    post_latencies = [m["post_call_latency_sec"] for m in metrics]
    
    all_chunk_times = []
    for m in metrics:
        for c in m.get("chunk_metrics", []):
            all_chunk_times.append(c["proc_time_sec"])
            
    print("=== Table 1 Markdown ===")
    headers = [
        "Ticker", "Fiscal Period", "Audio Duration", "ASR Time", "ASR RTF",
        "Diarization Time", "Diar RTF", "Total RTF", "Post-Call Latency",
        "Queue Drained", "Q&A Segments", "5-Min SLA"
    ]
    header_str = "| " + " | ".join(headers) + " |"
    sep_str = "| " + " | ".join([":---"] * len(headers)) + " |"
    print(header_str)
    print(sep_str)
    
    table_rows = []
    for m in metrics:
        ticker = f"**{m['ticker']}**"
        fiscal = m["fiscal_period"]
        dur_min = f"{m['audio_duration_sec'] / 60.0:.1f} min"
        asr_time = f"{m['asr_infer_time_sec']:.1f}s"
        asr_rtf = f"{m['asr_rtf']:.4f}"
        diar_time = f"{m['diarization_time_sec']:.1f}s"
        diar_rtf = f"{m['diarization_rtf']:.4f}"
        tot_rtf = f"{m['total_rtf']:.4f}"
        post_lat = f"{m['post_call_latency_sec']:.2f}s"
        queue_dr = "YES" if m["queue_drained"] else "NO"
        qa_segs = str(m["qa_segments"])
        sla_stat = f"**{m['sla_status']}**"
        
        row = f"| {ticker} | {fiscal} | {dur_min} | {asr_time} | {asr_rtf} | {diar_time} | {diar_rtf} | {tot_rtf} | {post_lat} | {queue_dr} | {qa_segs} | {sla_stat} |"
        table_rows.append(row)
        print(row)
        
    print("\n=== Aggregates & Stats ===")
    print(f"Total Audio Ingested: {total_audio_sec:.1f}s ({total_audio_sec / 3600.0:.2f} hours)")
    print(f"Total ASR Inference Time: {total_asr_sec:.1f}s")
    print(f"ASR RTF: Min = {min(asr_rtfs):.4f}, Max = {max(asr_rtfs):.4f}, Mean = {sum(asr_rtfs)/len(asr_rtfs):.4f}")
    print(f"Total GPU Diarization Time: {total_diar_sec:.1f}s")
    print(f"Diarization RTF: Min = {min(diar_rtfs):.4f}, Max = {max(diar_rtfs):.4f}, Mean = {sum(diar_rtfs)/len(diar_rtfs):.4f}")
    print(f"Total RTF: Min = {min(total_rtfs):.4f}, Max = {max(total_rtfs):.4f}, Mean = {sum(total_rtfs)/len(total_rtfs):.4f}")
    print(f"Post-Call Latency: Min = {min(post_latencies):.2f}s, Max = {max(post_latencies):.2f}s, Mean = {sum(post_latencies)/len(post_latencies):.2f}s ({sum(post_latencies)/len(post_latencies)/60.0:.2f} minutes)")
    print(f"Per-Chunk Processing Time: Min = {min(all_chunk_times):.2f}s, Max = {max(all_chunk_times):.2f}s, Mean = {sum(all_chunk_times)/len(all_chunk_times):.2f}s (Total chunks: {len(all_chunk_times)})")

if __name__ == "__main__":
    generate_table_and_stats()
