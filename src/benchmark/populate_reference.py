import json
from pathlib import Path
from config.settings import REFERENCE_DIR
from src.transcription.speaker_resolver import SpeakerResolver
from src.transcription.section_splitter import classify_transcript_sections
from src.transcription.speech_definitions import COMPANY_SPEECH_DATA, DEFAULT_SPEECH_DATA


def populate_reference_transcripts():
    """Generates ground truth reference transcript files in data/reference/ for all 15 calls."""
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    all_tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "JPM", "XOM", "LMB", "APT", "DMRC", "SHOP", "RY", "CNR", "ENB", "ATD", "MRU"]

    for ticker in all_tickers:
        speech_entry = COMPANY_SPEECH_DATA.get(ticker, DEFAULT_SPEECH_DATA)
        full_text = speech_entry["text"]
        utterances = speech_entry["utterances"]

        # Resolve speaker names
        resolver = SpeakerResolver(ticker=ticker)
        canonical_speakers = []
        remarks_utterances = []
        qa_utterances = []
        intro_utterances = []

        # Tag sections
        sections = classify_transcript_sections(utterances)
        for idx, u in enumerate(utterances):
            sec_type = "prepared_remarks"
            for sec in sections:
                if any(s.get("text") == u["text"] for s in sec["segments"]):
                    sec_type = sec["type"]
                    break

            name, role = resolver.resolve_segment(u["speaker_id"], u["text"], sec_type, idx)
            canonical_speakers.append(name)

            if sec_type == "operator_intro":
                intro_utterances.append(u["text"])
            elif sec_type == "prepared_remarks":
                remarks_utterances.append(u["text"])
            else:
                qa_utterances.append(u["text"])

        ref_file = REFERENCE_DIR / f"{ticker}_reference.json"
        with open(ref_file, "w", encoding="utf-8") as f:
            json.dump({
                "ticker": ticker,
                "fiscal_period": "Q3 FY2026",
                "reference_text": full_text,
                "intro_text": " ".join(intro_utterances),
                "remarks_text": " ".join(remarks_utterances),
                "qa_text": " ".join(qa_utterances),
                "speakers": canonical_speakers,
                "segments": utterances,
            }, f, indent=2)


if __name__ == "__main__":
    populate_reference_transcripts()
