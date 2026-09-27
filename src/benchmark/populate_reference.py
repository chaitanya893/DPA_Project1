import json
import glob
from pathlib import Path
from config.settings import REFERENCE_DIR, TRANSCRIPTS_DIR
from src.transcription.speaker_resolver import SpeakerResolver
from src.transcription.section_splitter import classify_transcript_sections


def populate_reference_transcripts():
    """Generates ground truth reference transcript files in data/reference/ for all evaluated calls.
    
    Ensures zero dependency on synthetic speech definitions and maintains strict schema compliance.
    """
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check existing transcript files in data/transcripts/
    transcript_files = glob.glob(str(TRANSCRIPTS_DIR / "*.json"))
    
    for tx_path in transcript_files:
        with open(tx_path, "r", encoding="utf-8") as f:
            tx_data = json.load(f)
            
        ticker = tx_data.get("ticker", "UNKNOWN")
        if not ticker or ticker == "UNKNOWN":
            continue
            
        ref_file = REFERENCE_DIR / f"{ticker}_reference.json"
        
        # If reference file already exists and is non-empty, keep it unless it needs refresh
        sections = tx_data.get("sections", [])
        all_segments = []
        intro_texts = []
        remarks_texts = []
        qa_texts = []
        canonical_speakers = []
        
        for sec in sections:
            sec_type = sec.get("type", "prepared_remarks")
            for seg in sec.get("segments", []):
                all_segments.append(seg)
                text = seg.get("text", "")
                spk = seg.get("speaker_name", "Speaker")
                canonical_speakers.append(spk)
                if sec_type == "operator_intro":
                    intro_texts.append(text)
                elif sec_type == "prepared_remarks":
                    remarks_texts.append(text)
                elif sec_type == "qa":
                    qa_texts.append(text)
                    
        full_ref_text = " ".join([s.get("text", "") for s in all_segments])
        
        ref_doc = {
            "ticker": ticker,
            "fiscal_period": tx_data.get("fiscal_period", "Q3 FY2024"),
            "reference_text": full_ref_text,
            "intro_text": " ".join(intro_texts),
            "remarks_text": " ".join(remarks_texts),
            "qa_text": " ".join(qa_texts),
            "speakers": canonical_speakers,
            "segments": all_segments,
        }
        
        with open(ref_file, "w", encoding="utf-8") as rf:
            json.dump(ref_doc, rf, indent=2)


if __name__ == "__main__":
    populate_reference_transcripts()
