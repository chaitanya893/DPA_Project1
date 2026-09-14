import unittest
from src.benchmark.normalizer import normalize_text
from src.benchmark.metrics import compute_wer, compute_cer, compute_entity_accuracy, compute_diarization_error_rate


class TestBenchmarkMetrics(unittest.TestCase):
    def test_normalizer_financial_numbers(self):
        """Tests financial number, percentage, and currency expansion/contraction."""
        text = "Today revenue reached $85.8B, up 5% with gross margin of 46.3% and cash of $450M."
        norm = normalize_text(text)
        self.assertIn("85.8 billion dollars", norm)
        self.assertIn("5 percent", norm)
        self.assertIn("46.3 percent", norm)
        self.assertIn("450 million dollars", norm)

    def test_normalizer_filler_words_and_contractions(self):
        """Tests that filler words ('um', 'uh') are stripped and contractions expanded."""
        text = "Um, we're pleased to say, uh, that's a record quarter."
        norm = normalize_text(text)
        self.assertNotIn("um", norm.split())
        self.assertNotIn("uh", norm.split())
        self.assertIn("we are pleased to say", norm)
        self.assertIn("that is a record quarter", norm)

    def test_compute_wer_and_cer(self):
        """Tests Levenshtein Word Error Rate (WER) and Character Error Rate (CER)."""
        ref = "Apple revenue reached 85.8 billion dollars"
        hyp_exact = "Apple revenue reached 85.8 billion dollars"
        hyp_error = "Apple revenue reached 85.8 million dollars"

        self.assertEqual(compute_wer(ref, hyp_exact), 0.0)
        self.assertEqual(compute_cer(ref, hyp_exact), 0.0)

        # 1 word substituted out of 6 words -> WER = 1/6 = ~0.1667
        wer_err = compute_wer(ref, hyp_error)
        self.assertAlmostEqual(wer_err, 1/6, places=2)

    def test_entity_level_accuracy(self):
        """Tests weighted entity-level accuracy calculation."""
        ref = "Tim Cook announced Apple Q3 revenue of $85.8 billion and EPS of $1.40."
        hyp = "Tim Cook announced Apple Q3 revenue of $85.8 billion and EPS of $1.40."

        res = compute_entity_accuracy(ref, hyp)
        self.assertEqual(res["overall_weighted_entity_accuracy"], 1.0)
        self.assertIn("monetary_amounts", res)
        self.assertIn("person_names", res)

    def test_diarization_error_rate(self):
        """Tests Speaker Attribution and DER calculation."""
        ref_speakers = ["Operator", "Tim Cook", "Luca Maestri", "Shannon Cross"]
        hyp_speakers = ["Operator", "Tim Cook", "Luca Maestri", "Shannon Cross"]

        res = compute_diarization_error_rate(ref_speakers, hyp_speakers)
        self.assertEqual(res["der"], 0.0)
        self.assertEqual(res["speaker_attribution_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
