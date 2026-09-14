# Earnings Call Capture & Transcription Pipeline (Assignment 1)

An automated, open-source data engineering and ASR pipeline designed to discover corporate earnings calls, capture live/replay audio streams, produce speaker-labelled timestamped transcripts within a 5-minute post-call window, and benchmark transcription accuracy against official ground-truth references.

---

## 📁 Repository Structure

```text
DPA_Project1/
├── config/
│   ├── universe.csv             # 25 Curated US/Canadian target companies
│   └── settings.py              # Centralized configuration & rate limits
├── data/
│   ├── audio/                   # Standardized 16 kHz Mono WAV audio files
│   │   ├── capture_manifest.csv # Metadata manifest for captured calls
│   │   └── capture_failures.log # Transparent capture failure log
│   ├── transcripts/             # Structured deliverable JSON transcripts
│   ├── reference/               # Ground-truth reference transcripts for benchmarking
│   └── samples/                 # Sample data
├── docs/
│   ├── SOURCE_COMPLIANCE.md     # Scraper ToS & legal compliance audit log
│   ├── DIAL_IN_EXCLUSION.md     # Paragraph memo on why telephone dial-in is out of scope
│   ├── EVENT_DISCOVERY_MEMO.md  # 1-page memo on event discovery routes & vendor analysis
│   └── FINAL_MEMO.md            # Comprehensive 5-8 page benchmark report & 500-company cost model
├── src/
│   ├── db/                      # Database schema models (SQLAlchemy) & session manager
│   │   ├── models.py
│   │   └── session.py
│   ├── discovery/               # SEC EDGAR 8-K, IR scrapers, Webcast Vendor classifier
│   │   ├── sec_edgar.py
│   │   ├── vendor_classifier.py
│   │   ├── ir_scraper.py
│   │   └── pipeline.py
│   ├── capture/                 # Stream downloading & 16 kHz Mono WAV standardizer
│   │   ├── audio_standardizer.py
│   │   ├── speech_synthesizer.py
│   │   ├── stream_downloader.py
│   │   └── pipeline.py
│   ├── transcription/           # Streaming VAD chunker, ASR pool, Diarizer & Speaker Resolver
│   │   ├── vad_chunker.py
│   │   ├── benchmark_models.py
│   │   ├── asr_engine.py
│   │   ├── speaker_resolver.py
│   │   ├── section_splitter.py
│   │   └── pipeline.py
│   ├── benchmark/               # Custom financial normalizer, WER/CER/Entity evaluator
│   │   ├── normalizer.py
│   │   ├── metrics.py
│   │   ├── populate_reference.py
│   │   ├── evaluator.py
│   │   └── memo_generator.py
│   ├── utils/                   # Rate limiter, correlation-ID structured logger, DB viewer
│   │   ├── logger.py
│   │   ├── rate_limiter.py
│   │   ├── view_db.py
│   │   └── view_transcripts.py
│   ├── transcribe_file.py       # Single-command CLI tool to transcribe ANY custom audio file
│   └── run_all.py               # Master script running full pipeline end-to-end with 1 command
├── tests/                       # Automated unit test suite (100% passing)
│   ├── test_universe.py
│   ├── test_sec_edgar.py
│   ├── test_vendor_classifier.py
│   ├── test_audio_standardizer.py
│   ├── test_transcription_pipeline.py
│   └── test_benchmark_metrics.py
├── run_tests.py                 # Instant test runner script
├── requirements.txt             # Pinned project dependencies
└── README.md
```

---

## ⚡ Quickstart Guide

### 1. Run All Tests
Verify all 10 unit tests across all components:
```bash
python run_tests.py
```

### 2. Execute Entire Pipeline (One Single Command)
Runs Phase 1 (Discovery) $\rightarrow$ Phase 2 (Audio Capture) $\rightarrow$ Phase 3 (Transcription) $\rightarrow$ Phase 4 (Benchmarking & Final Memo):
```bash
python -m src.run_all
```

### 3. Inspect Database Tables
```bash
python -m src.utils.view_db
```

### 4. Inspect Generated JSON Transcripts
```bash
python -m src.utils.view_transcripts
```

### 5. Transcribe Any Custom Audio File (MP3/MP4/WAV of Any Length)
```bash
python -m src.transcribe_file "path/to/any_audio.mp3" --ticker AAPL
```

---

## 📊 Deliverables Summary

1. **Phase 0 Deliverable**: [config/universe.csv](config/universe.csv) & [docs/SOURCE_COMPLIANCE.md](docs/SOURCE_COMPLIANCE.md)
2. **Phase 1 Deliverable**: Populated `event_registry` database table & [docs/EVENT_DISCOVERY_MEMO.md](docs/EVENT_DISCOVERY_MEMO.md)
3. **Phase 2 Deliverable**: 15 Standardized 16 kHz Mono WAV audios, `data/audio/capture_manifest.csv`, and [docs/DIAL_IN_EXCLUSION.md](docs/DIAL_IN_EXCLUSION.md)
4. **Phase 3 Deliverable**: 15 Structured JSON Transcripts in `data/transcripts/` with `prepared_remarks` vs `qa` split
5. **Phase 4 Deliverable**: Full Benchmarking Report & 5-8 Page Research Memo in [docs/FINAL_MEMO.md](docs/FINAL_MEMO.md)
