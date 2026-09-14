import argparse
import json
import os
import sys
import time
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.capture.audio_standardizer import convert_to_standard_wav
from src.transcription.asr_engine import transcribe_audio_pipeline
from src.transcription.speaker_resolver import SpeakerResolver
from src.transcription.section_splitter import classify_transcript_sections
from src.utils.logger import setup_logger

logger = setup_logger("transcribe_file")


def transcribe_any_audio_file(
    input_audio_path: str,
    ticker: str = "AAPL",
    output_json_path: str = None,
) -> str:
    """Takes ANY input audio file (MP3, MP4, M4A, AAC, WAV, OGG, etc.) of ANY duration
    (e.g., 30 mins, 1 hour), converts it to 16kHz Mono WAV, chunks it into 60s streaming
    segments, resolves speaker names, splits into Remarks vs Q&A, and outputs standardized JSON.
    """
    if not os.path.exists(input_audio_path):
        raise FileNotFoundError(f"Input file not found: {input_audio_path}")

    start_time = time.time()
    input_file = Path(input_audio_path)
    file_ext = input_file.suffix.lower()

    print("\n" + "=" * 80)
    print(f"  [AUDIO] TRANSCRIBING CUSTOM AUDIO FILE: {input_file.name}")
    print(f"  [FORMAT] Input Format: {file_ext.upper()} | Ticker: {ticker}")
    print("=" * 80)

    # 1. Step 1: Standardize ANY format to 16kHz Mono 16-bit PCM WAV
    temp_wav_path = str(input_file.parent / f"standardized_{input_file.stem}.wav")
    print(f"\n[1/4] Converting {file_ext} to Standardized 16kHz Mono 16-bit PCM WAV...")
    stats = convert_to_standard_wav(str(input_file), temp_wav_path)
    print(f"      [OK] Audio Duration: {stats['duration_sec']}s ({round(stats['duration_sec']/60, 2)} mins) | Sample Rate: {stats['sample_rate']} Hz")

    # 2. Step 2: Run Streaming Chunked ASR Speech Recognition
    print(f"\n[2/4] Transcribing 60s streaming chunks using faster-whisper ASR...")
    asr_res = transcribe_audio_pipeline(temp_wav_path, ticker=ticker)
    raw_segments = asr_res["segments"]
    print(f"      [OK] Generated {len(raw_segments)} speech segments | RTF: {asr_res['rtf']}")

    # 3. Step 3: Diarization, Speaker Resolution & Section Splitting
    print(f"\n[3/4] Resolving Speaker Names, Executive Roles & Q&A Sections...")
    sections = classify_transcript_sections(raw_segments)
    resolver = SpeakerResolver(ticker=ticker)

    resolved_segments = []
    for idx, seg in enumerate(raw_segments):
        sec_type = "prepared_remarks"
        for sec in sections:
            if any(s.get("start") == seg["start"] for s in sec["segments"]):
                sec_type = sec["type"]
                break

        name, role = resolver.resolve_segment(
            speaker_id=seg["speaker_id"],
            text=seg["text"],
            section_type=sec_type,
            segment_index=idx,
        )

        resolved_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "speaker_id": seg["speaker_id"],
            "speaker_name": name,
            "speaker_role": role,
            "text": seg["text"],
            "confidence": seg.get("confidence", 0.94),
        })

    final_sections = classify_transcript_sections(resolved_segments)

    # 4. Step 4: Construct Standard JSON Output
    if not output_json_path:
        output_json_path = str(input_file.parent / f"{input_file.stem}_transcript.json")

    transcript_doc = {
        "event_id": f"EVT_CUSTOM_{ticker}_{int(time.time())}",
        "ticker": ticker,
        "fiscal_period": "Custom Recording",
        "call_datetime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "language": "en",
        "sections": final_sections,
        "pipeline": {
            "asr_model": "faster-whisper-v3-large",
            "diarizer": "pyannote.audio-3.1",
            "version": "1.0.0",
            "rtf": asr_res["rtf"],
            "total_processing_time_sec": round(time.time() - start_time, 2),
        },
    }

    with open(output_json_path, mode="w", encoding="utf-8") as f:
        json.dump(transcript_doc, f, indent=2)

    total_time = round(time.time() - start_time, 2)
    print(f"\n[4/4] JSON Transcript successfully saved to: {output_json_path}")
    print(f"      Total Processing Latency: {total_time}s")
    print("=" * 80 + "\n")

    return output_json_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe ANY audio/video file of ANY duration.")
    parser.add_argument("file_path", help="Path to input audio file (.mp3, .mp4, .wav, .m4a, etc.)")
    parser.add_argument("--ticker", default="AAPL", help="Company ticker (e.g. AAPL, MSFT, TSLA)")
    parser.add_argument("--output", default=None, help="Path to output JSON file")

    args = parser.parse_args()
    transcribe_any_audio_file(args.file_path, ticker=args.ticker, output_json_path=args.output)
