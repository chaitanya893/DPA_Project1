import unittest
import os
from src.validation.validate_all import (
    validate_universe,
    validate_audio_capture,
    validate_transcripts,
    run_full_system_validation,
)
from src.benchmark.evaluator import run_benchmark_evaluation
from src.benchmark.metrics import compute_wer, compute_cer, compute_entity_accuracy


class TestValidationGates(unittest.TestCase):
    def test_gate1_universe_validation(self):
        res = validate_universe()
        self.assertEqual(res['status'], 'PASS')
        self.assertEqual(res['total_companies'], 25)
        self.assertEqual(res['us_large_cap'], 10)
        self.assertEqual(res['us_small_cap'], 5)
        self.assertEqual(res['canadian_tsx_english'], 7)
        self.assertEqual(res['canadian_bilingual'], 3)

    def test_gate2_audio_capture_validation(self):
        res = validate_audio_capture()
        self.assertEqual(res['status'], 'PASS')
        self.assertGreaterEqual(res['valid_wav_count'], 12)
        self.assertGreaterEqual(res['manifest_records'], 15)

    def test_gate3_transcript_schema_validation(self):
        res = validate_transcripts()
        self.assertEqual(res['status'], 'PASS')
        self.assertGreaterEqual(res['total_transcripts'], 12)
        self.assertEqual(res['schema_errors_count'], 0)

    def test_gate4_benchmark_evaluator(self):
        eval_res = run_benchmark_evaluation()
        summary = eval_res['summary']
        self.assertIn('avg_raw_wer', summary)
        self.assertIn('avg_normalized_wer', summary)
        self.assertIn('avg_entity_accuracy', summary)
        self.assertIn('avg_der', summary)
        self.assertIn('average_rtf', summary)
        self.assertLessEqual(summary['avg_normalized_wer'], 0.05)
        self.assertGreaterEqual(summary['avg_entity_accuracy'], 0.90)


if __name__ == '__main__':
    unittest.main()
