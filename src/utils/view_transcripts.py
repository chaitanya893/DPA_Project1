import glob
import json
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from config.settings import TRANSCRIPTS_DIR


def view_latest_transcripts():
    """Prints a clean summary of generated structured JSON transcripts."""
    json_files = glob.glob(str(TRANSCRIPTS_DIR / "*.json"))

    print("\n" + "=" * 80)
    print(f"  [TRANSCRIPTS REPORT] ({len(json_files)} Files in {TRANSCRIPTS_DIR})")
    print("=" * 80)

    if not json_files:
        print("No transcript JSON files found. Run 'python -m src.transcription.pipeline' first.")
        print("=" * 80 + "\n")
        return

    for path in json_files[:3]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        segs = data.get("segments", [])
        if not segs and "sections" in data:
            segs = [seg for sec in data["sections"] for seg in sec.get("segments", [])]

        print(f"\n[FILE] Ticker: {data.get('ticker')} | Period: {data.get('fiscal_period')} | Language: {data.get('language')}")
        print(f"       ASR Engine: {data.get('pipeline', {}).get('asr_model')} | RTF: {data.get('pipeline', {}).get('rtf')}")
        print(f"       Sections: {[s['type'] for s in data.get('sections', [])]}")
        print(f"       Total Aligned Segments: {len(segs)}")
        print("       Sample Transcript Excerpt:")
        for seg in segs[:3]:
            print(f"         [{seg['start']}s - {seg['end']}s] {seg['speaker_name']} ({seg['speaker_role']}): \"{seg['text'][:85]}...\"")
        print("-" * 80)

    if len(json_files) > 3:
        print(f"... and {len(json_files) - 3} more company transcripts stored in data/transcripts/.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    view_latest_transcripts()
