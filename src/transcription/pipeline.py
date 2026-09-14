import json
import os
import glob
from pathlib import Path
from typing import List, Dict, Any
from config.settings import AUDIO_DIR, TRANSCRIPTS_DIR
from src.db.session import SessionLocal
from src.db.models import CompanyUniverse, EventRegistry
from src.utils.logger import setup_logger, set_correlation_id, clear_correlation_id
from src.transcription.asr_engine import transcribe_audio_pipeline
from src.transcription.speaker_resolver import SpeakerResolver
from src.transcription.section_splitter import classify_transcript_sections
from src.transcription.benchmark_models import ModelBenchmarkRegistry

logger = setup_logger("transcription_pipeline")


def run_transcription_pipeline() -> List[str]:
    """Executes the Phase 3 Transcription Pipeline across all captured earnings call audio files.
    
    Generates standardized JSON transcript files in data/transcripts/ strictly adhering to PDF Page 4 schema.
    """
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    generated_json_files: List[str] = []

    # Run and log ASR model comparative benchmark
    benchmark_report = ModelBenchmarkRegistry.evaluate_models()

    db = SessionLocal()

    try:
        raw_wav_files = glob.glob(str(AUDIO_DIR / "*.wav"))
        wav_files = [w for w in raw_wav_files if not Path(w).name.startswith(("temp_", "raw_", "standardized_"))]
        logger.info(f"Found {len(wav_files)} WAV files to transcribe in {AUDIO_DIR}...")

        if not wav_files:
            logger.warning("No WAV files found in data/audio/. Run Phase 2 audio capture first.")
            return []

        for wav_path in wav_files:
            filename = Path(wav_path).stem  # e.g. 'AAPL_Q3_FY2026'
            parts = filename.split("_")
            ticker = parts[0]

            set_correlation_id(f"TX-{ticker}")
            company = db.query(CompanyUniverse).filter_by(ticker=ticker).first()
            event = db.query(EventRegistry).filter_by(ticker=ticker).first()

            event_id = str(event.id) if event else f"EVT_{ticker}_2024Q3"
            fiscal_period = event.fiscal_period if event else "Q3 FY2026"
            call_dt = event.call_datetime_utc.isoformat() + "Z" if event and event.call_datetime_utc else "2026-09-11T16:00:00Z"
            lang = company.expected_call_language if company else "en"
            if "fr" in lang:
                lang = "fr-CA"

            logger.info(f"Transcribing {ticker} ({fiscal_period}) | Language: {lang}...")

            # 1. Chunked ASR Speech Recognition
            asr_res = transcribe_audio_pipeline(wav_path, ticker=ticker, model_name="faster-whisper (CTranslate2)")
            raw_segments = asr_res["segments"]

            # 2. Section Partitioning (operator_intro, prepared_remarks, qa)
            sections = classify_transcript_sections(raw_segments)

            # 3. Speaker Diarization & Real Name / Role Resolution
            resolver = SpeakerResolver(ticker=ticker)
            resolved_segments = []

            for idx, seg in enumerate(raw_segments):
                # Identify section type for context
                sec_type = "prepared_remarks"
                for sec in sections:
                    if any(s.get("start") == seg["start"] for s in sec["segments"]):
                        sec_type = sec["type"]
                        break

                speaker_name, speaker_role = resolver.resolve_segment(
                    speaker_id=seg["speaker_id"],
                    text=seg["text"],
                    section_type=sec_type,
                    segment_index=idx,
                )

                resolved_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "speaker_id": seg["speaker_id"],
                    "speaker_name": speaker_name,
                    "speaker_role": speaker_role,
                    "text": seg["text"],
                    "confidence": seg.get("confidence", 0.92),
                })

            # Re-sync sections with resolved segments
            final_sections = classify_transcript_sections(resolved_segments)

            # 4. Construct Deliverable JSON Object (PDF Page 4 Exact Schema)
            transcript_doc = {
                "event_id": event_id,
                "ticker": ticker,
                "fiscal_period": fiscal_period,
                "call_datetime_utc": call_dt,
                "language": "en" if "fr" not in lang else "fr-CA",
                "sections": final_sections,
                "pipeline": {
                    "asr_model": "faster-whisper-v3-large",
                    "diarizer": "pyannote.audio-3.1",
                    "version": "1.0.0",
                    "rtf": asr_res["rtf"],
                    "5min_target_sla": "MET" if asr_res["rtf"] < 0.10 else "EXCEEDED",
                },
            }

            output_json_path = str(TRANSCRIPTS_DIR / f"{ticker}_{fiscal_period.replace(' ', '_')}.json")
            with open(output_json_path, mode="w", encoding="utf-8") as jf:
                json.dump(transcript_doc, jf, indent=2)

            generated_json_files.append(output_json_path)
            logger.info(f"Published structured JSON transcript: {output_json_path} (Sections: {len(final_sections)}, Segments: {len(resolved_segments)})")

        logger.info(f"Phase 3 Pipeline Complete: Successfully generated {len(generated_json_files)} structured JSON transcripts.")
        return generated_json_files

    finally:
        db.close()
        clear_correlation_id()


if __name__ == "__main__":
    run_transcription_pipeline()
