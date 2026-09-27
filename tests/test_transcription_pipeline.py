import unittest
from src.transcription.vad_chunker import deduplicate_overlap_text
from src.transcription.speaker_resolver import SpeakerResolver
from src.transcription.section_splitter import classify_transcript_sections
from src.transcription.benchmark_models import ModelBenchmarkRegistry


class TestTranscriptionPipeline(unittest.TestCase):
    def test_deduplicate_overlap_text(self):
        """Tests that overlapping words between consecutive audio chunks are seamlessly deduplicated."""
        prev = "Today Apple is reporting a new June quarter revenue record"
        curr = "quarter revenue record of 85.8 billion dollars"
        stitched = deduplicate_overlap_text(prev, curr)
        self.assertEqual(stitched, "of 85.8 billion dollars")

    def test_speaker_resolver_apple(self):
        """Tests speaker identification for dynamic introductory cues."""
        resolver = SpeakerResolver(ticker="AAPL")

        # Intro / Operator
        name0, role0 = resolver.resolve_segment("S0", "Welcome to Apple conference call. I will turn the call over to Tim Cook, CEO.", "operator_intro", 0)
        self.assertEqual(role0, "Operator")

        # Remarks / Executive
        name1, role1 = resolver.resolve_segment("S1", "Thank you Suhasini. Today we report strong growth.", "prepared_remarks", 1)
        self.assertEqual(name1, "Tim Cook")
        self.assertEqual(role1, "CEO")


    def test_section_splitter(self):
        """Tests partitioning segments into operator_intro, prepared_remarks, and qa."""
        segments = [
            {"start": 0.0, "end": 10.0, "text": "Good morning and welcome to the conference call."},
            {"start": 10.0, "end": 20.0, "text": "I will turn the call over to our CEO for prepared remarks."},
            {"start": 20.0, "end": 50.0, "text": "Thank you. Our revenue reached 60 billion dollars."},
            {"start": 50.0, "end": 60.0, "text": "We will now begin the question-and-answer session."},
            {"start": 60.0, "end": 80.0, "text": "Our first question comes from Morgan Stanley."},
        ]
        sections = classify_transcript_sections(segments)
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0]["type"], "operator_intro")
        self.assertEqual(sections[1]["type"], "prepared_remarks")
        self.assertEqual(sections[2]["type"], "qa")

    def test_benchmark_models_evaluation(self):
        """Tests that 3 ASR models are benchmarked and evaluate RTF properly."""
        report = ModelBenchmarkRegistry.evaluate_models()
        self.assertIn("models", report)
        self.assertEqual(len(report["models"]), 3)
        self.assertEqual(report["recommended_default"], "faster-whisper (CTranslate2)")


if __name__ == "__main__":
    unittest.main()
