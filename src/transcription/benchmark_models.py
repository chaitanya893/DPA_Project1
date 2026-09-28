import os
import time
import subprocess
import psutil
import torch
from pathlib import Path
from typing import Dict, List, Any
from faster_whisper import WhisperModel
from src.utils.logger import setup_logger

logger = setup_logger("benchmark_models")


class ModelBenchmarkRegistry:
    """Evaluates and benchmarks ASR engines on standard 10-minute audio clips."""

    @classmethod
    def benchmark_faster_whisper(
        cls,
        clip_path: str,
        device: str = "cpu",
        compute_type: str = "int8",
        threads: int = 8
    ) -> Dict[str, Any]:
        """Runs measured benchmark for faster-whisper."""
        model = WhisperModel("small.en", device=device, compute_type=compute_type, cpu_threads=threads)
        
        # Warmup
        segs, _ = model.transcribe(clip_path, beam_size=1)
        _ = list(segs)
        
        # Measured run
        if device == "cuda":
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
            
        process = psutil.Process(os.getpid())
        ram_before = process.memory_info().rss
        
        t0 = time.perf_counter()
        segs, info = model.transcribe(clip_path, beam_size=1)
        seg_list = list(segs)
        if device == "cuda":
            torch.cuda.synchronize()
        t1 = time.perf_counter()
        
        wall_time = t1 - t0
        rtf = wall_time / 600.0
        ram_after = process.memory_info().rss
        peak_ram_mb = max(ram_before, ram_after) / (1024 * 1024)
        peak_vram_mb = (torch.cuda.max_memory_allocated() / (1024 * 1024)) if device == "cuda" else 0.0
        
        return {
            "library": "faster-whisper",
            "device": device,
            "compute_type": compute_type,
            "wall_time_sec": round(wall_time, 2),
            "rtf": round(rtf, 4),
            "peak_ram_mb": round(peak_ram_mb, 1),
            "peak_vram_mb": round(peak_vram_mb, 1),
            "segments": seg_list
        }

    @classmethod
    def benchmark_whisper_cpp(
        cls,
        clip_path: str,
        device: str = "cpu",
        binary_path: str = "data/benchmark/whisper_cpp/cpu/Release/whisper-cli.exe",
        model_path: str = "data/benchmark/whisper_cpp/ggml-small.en.bin",
        output_prefix: str = "data/benchmark/outputs/temp"
    ) -> Dict[str, Any]:
        """Runs measured benchmark for whisper.cpp binary."""
        cmd = [
            binary_path,
            "-m", model_path,
            "-f", clip_path,
            "-l", "en",
            "-otxt",
            "-of", output_prefix
        ]
        if device == "cpu":
            cmd.extend(["-t", "8", "-ng"])
        else:
            cmd.extend(["-t", "4"])
            
        # Warmup
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Measured run
        t0 = time.perf_counter()
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p = psutil.Process(proc.pid)
        peak_ram = 0
        while proc.poll() is None:
            try:
                mem = p.memory_info().rss
                if mem > peak_ram:
                    peak_ram = mem
            except Exception:
                pass
            time.sleep(0.05)
        t1 = time.perf_counter()
        proc.wait()
        
        wall_time = t1 - t0
        rtf = wall_time / 600.0
        peak_ram_mb = round(peak_ram / (1024 * 1024), 1)
        
        return {
            "library": "whisper.cpp",
            "device": device,
            "compute_type": "ggml-small.en",
            "wall_time_sec": round(wall_time, 2),
            "rtf": round(rtf, 4),
            "peak_ram_mb": peak_ram_mb,
            "peak_vram_mb": 0.0
        }
