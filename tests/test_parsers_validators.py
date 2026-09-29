import datetime
import unittest
from src.utils.date_parser import parse_call_datetime_to_utc
from src.discovery.vendor_classifier import classify_vendor_from_url, classify_vendor_from_html
from src.discovery.sec_edgar import extract_fiscal_period_from_text, extract_call_datetime_from_text
from src.benchmark.normalizer import normalize_financial_transcript
from src.benchmark.metrics import compute_wer, compute_cer, compute_entity_accuracy
from src.transcription.vad_chunker import stitch_overlapping_segments
from src.validation.validate_all import validate_transcript_schema


class TestParsersAndValidators(unittest.TestCase):
    """Meaningful test coverage for parsers and validators as strictly specified by Assignment 1 PDF."""

    # 1. Date / Time / Timezone Parser Tests & Real Press Release Phrase Examples
    def test_date_parser_full(self):
        utc_dt, tz_pub = parse_call_datetime_to_utc("October 29, 2024", "5:00 PM", "ET")
        assert utc_dt is not None
        assert tz_pub == "ET"
        assert utc_dt.year == 2024
        assert utc_dt.month == 10

    def test_date_parser_missing_time_or_tz(self):
        utc_dt, tz_pub = parse_call_datetime_to_utc("October 29, 2024", None, None)
        assert utc_dt is None

    def test_real_phrase_apple_8k(self):
        text = "Apple today announced results for its fourth quarter of fiscal 2024. Apple will hold a conference call at 2:00 p.m. PT on Thursday, October 31, 2024"
        fp = extract_fiscal_period_from_text(text)
        dt_utc, tz_clean, _ = extract_call_datetime_from_text(text, "2024-10-31")
        assert fp == "Q4 FY2024"
        assert dt_utc is not None
        assert tz_clean == "PT"
        assert dt_utc.hour == 21  # 2:00 PM PDT (UTC-7) = 21:00 UTC

    def test_real_phrase_microsoft_8k(self):
        text = "Satya Nadella and Amy Hood will host a conference call and webcast at 2:30 p.m. Pacific time (5:30 p.m. Eastern time) today to discuss details of the company results for the first quarter of fiscal 2025."
        fp = extract_fiscal_period_from_text(text)
        dt_utc, tz_clean, _ = extract_call_datetime_from_text(text, "2024-10-30")
        assert fp == "Q1 FY2025"
        assert dt_utc is not None
        assert "PACIFIC" in tz_clean or "PT" in tz_clean
        assert dt_utc.hour == 21 and dt_utc.minute == 30  # 2:30 PM PDT = 21:30 UTC

    def test_real_phrase_jpmorgan_8k(self):
        text = "JPMorgan Chase & Co. will host a conference call today, July 14, 2026, at 8:30 a.m. (ET) to present second-quarter 2026 financial results."
        fp = extract_fiscal_period_from_text(text)
        dt_utc, tz_clean, _ = extract_call_datetime_from_text(text, "2026-07-14")
        assert fp == "Q2 FY2026"
        assert dt_utc is not None
        assert tz_clean == "ET"
        assert dt_utc.hour == 12 and dt_utc.minute == 30  # 8:30 AM EDT = 12:30 UTC

    def test_real_phrase_tesla_8k(self):
        text = "Tesla third quarter of 2024 financial results. Live webcast starts at 4:30 p.m. Central Time (CT) on October 23, 2024"
        fp = extract_fiscal_period_from_text(text)
        dt_utc, tz_clean, _ = extract_call_datetime_from_text(text, "2024-10-23")
        assert fp == "Q3 FY2024"
        assert dt_utc is not None
        assert "CT" in tz_clean or "CENTRAL" in tz_clean
        assert dt_utc.hour == 21 and dt_utc.minute == 30  # 4:30 PM CDT = 21:30 UTC

    def test_real_phrase_shopify_6k(self):
        text = "Shopify will hold a conference call on Tuesday, August 5, 2026 at 8:30 a.m. ET to discuss second-quarter 2026 financial results."
        fp = extract_fiscal_period_from_text(text)
        dt_utc, tz_clean, _ = extract_call_datetime_from_text(text, "2026-08-05")
        assert fp == "Q2 FY2026"
        assert dt_utc is not None
        assert tz_clean == "ET"
        assert dt_utc.hour == 12 and dt_utc.minute == 30  # 8:30 AM EDT = 12:30 UTC

    def test_real_phrase_exxon_ir(self):
        text = "ExxonMobil July 31, 2026 8:30 AM CDT 2Q 2026 Earnings Call"
        fp = extract_fiscal_period_from_text(text)
        dt_utc, tz_clean, _ = extract_call_datetime_from_text(text, "2026-07-31")
        assert fp == "Q2 FY2026"
        assert dt_utc is not None
        assert tz_clean == "CDT"
        assert dt_utc.hour == 13 and dt_utc.minute == 30  # 8:30 AM CDT = 13:30 UTC

    def test_real_phrase_permafix_ir(self):
        text = "Perma-Fix Reports Second Quarter 2026 Results. Second Quarter 2026 Conference Call August 12, 2026 at 4:30pm EDT"
        fp = extract_fiscal_period_from_text(text)
        dt_utc, tz_clean, _ = extract_call_datetime_from_text(text, "2026-08-12")
        assert fp == "Q2 FY2026"
        assert dt_utc is not None
        assert tz_clean == "EDT"
        assert dt_utc.hour == 20 and dt_utc.minute == 30  # 4:30 PM EDT = 20:30 UTC

    def test_real_phrase_walmart_headline(self):
        text = "Walmart reports second quarter results ... raises outlook for FY27"
        fp = extract_fiscal_period_from_text(text)
        assert fp == "Q2 FY2027"

    def test_real_phrase_richardson_headline(self):
        text = "Richardson Electronics Reports Fourth Quarter and Fiscal Year 2026 Results"
        fp = extract_fiscal_period_from_text(text)
        assert fp == "Q4 FY2026"

    # 2. Webcast Vendor Classifier Tests
    def test_vendor_classifier_q4(self):
        vendor = classify_vendor_from_url("https://events.q4inc.com/attendee/12345")
        assert vendor == "Q4 Inc"

    def test_vendor_classifier_notified(self):
        vendor = classify_vendor_from_url("https://event.notified.com/webcast/player")
        assert vendor == "Notified"

    def test_vendor_classifier_on24(self):
        vendor = classify_vendor_from_url("https://event.on24.com/wcc/r/98765")
        assert vendor == "ON24"

    def test_vendor_classifier_html(self):
        html = '<iframe src="https://services.choruscall.com/links/aapl.html"></iframe>'
        vendor, conf = classify_vendor_from_html(html)
        assert "Chorus Call" in vendor
        assert conf >= 0.85

    # 3. Financial Normalizer Tests
    def test_normalizer_currency_magnitudes(self):
        raw = "Revenue reached $85.8B with gross profit of $24.2 billion."
        norm = normalize_financial_transcript(raw)
        assert "85.8 billion dollars" in norm
        assert "24.2 billion dollars" in norm

    def test_normalizer_percentages(self):
        raw = "Gross margin was 46.3% and grew by 5 percent."
        norm = normalize_financial_transcript(raw)
        assert "46.3 percent" in norm

    def test_normalizer_contractions_and_fillers(self):
        raw = "Um, we're confident that, uh, it's growing."
        norm = normalize_financial_transcript(raw)
        assert "we are confident that it is growing" in norm
        assert "um" not in norm
        assert "uh" not in norm

    # 4. WER & CER Metric Tests
    def test_wer_calculation(self):
        ref = "Apple revenue reached eighty five billion dollars"
        hyp = "Apple revenue reached eighty five billion dollars"
        assert compute_wer(ref, hyp) == 0.0

        hyp_err = "Apple revenue reached eighty billion dollars"
        assert compute_wer(ref, hyp_err) > 0.0

    def test_cer_calculation(self):
        ref = "Microsoft Cloud"
        hyp = "Microsoft Cloud"
        assert compute_cer(ref, hyp) == 0.0

    # 5. 7-Class Entity Extractor Tests
    def test_entity_accuracy_extractor(self):
        ref = "Revenue was $10.5 billion, margin was 32.5%, CEO Tim Cook spoke on January 15, 2025."
        hyp = "Revenue was $10.5 billion, margin was 32.5%, CEO Tim Cook spoke on January 15, 2025."
        res = compute_entity_accuracy(ref, hyp)
        assert res["overall_weighted_entity_accuracy"] >= 0.95
        assert "monetary_amounts" in res
        assert "percentages" in res
        assert "person_names" in res

    # 6. Overlap Stitcher Tests
    def test_overlap_stitcher_deduplication(self):
        chunk_prev = [
            {"start": 0.0, "end": 5.0, "text": "Good morning and welcome to the call."},
            {"start": 5.0, "end": 10.0, "text": "I will turn the meeting over to our CEO."},
        ]
        chunk_next = [
            {"start": 7.0, "end": 10.0, "text": "I will turn the meeting over to our CEO."},
            {"start": 10.0, "end": 15.0, "text": "Thank you. Today we report solid results."},
        ]
        stitched = stitch_overlapping_segments(chunk_prev, chunk_next, overlap_sec=3.0)
        assert len(stitched) == 3
        assert stitched[0]["text"] == "Good morning and welcome to the call."
        assert stitched[-1]["text"] == "Thank you. Today we report solid results."

    # 7. JSON Schema Validator Tests
    def test_transcript_json_schema(self):
        valid_doc = {
            "event_id": "EVT_AAPL_Q3_FY2024",
            "ticker": "AAPL",
            "fiscal_period": "Q3 FY2024",
            "call_datetime_utc": "2024-10-31T21:00:00Z",
            "language": "en",
            "sections": [
                {
                    "type": "operator_intro",
                    "start": 0.0,
                    "end": 10.0,
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 10.0,
                            "speaker_id": "S0",
                            "speaker_name": "Conference Operator",
                            "speaker_role": "Operator",
                            "text": "Welcome to the Apple earnings call.",
                            "confidence": 0.95,
                        }
                    ]
                }
            ],
            "pipeline": {
                "asr_model": "faster-whisper-small.en",
                "diarizer": "pyannote-audio-3.1",
                "version": "1.0.0",
                "rtf": 0.08,
                "post_call_latency_sec": 4.2,
            }
        }
        is_valid, errs = validate_transcript_schema(valid_doc)
        assert is_valid is True
        assert len(errs) == 0
