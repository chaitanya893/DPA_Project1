import os
import tempfile
import unittest
from src.capture.audio_standardizer import create_mock_tone_wav, get_wav_properties, compute_sha256


class TestAudioStandardizer(unittest.TestCase):
    def test_standardized_audio_properties(self):
        """Validates that audio output strictly meets WAV 16kHz Mono 16-bit PCM standard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_wav = os.path.join(tmpdir, "test_call.wav")
            create_mock_tone_wav(test_wav, duration_sec=3)

            self.assertTrue(os.path.exists(test_wav), "Generated WAV file must exist")
            duration_sec, sample_rate, channels, bit_depth = get_wav_properties(test_wav)

            # Non-negotiable acceptance criteria from PDF
            self.assertEqual(sample_rate, 16000, f"Sample rate must be 16000 Hz, got {sample_rate}")
            self.assertEqual(channels, 1, f"Channels must be 1 (Mono), got {channels}")
            self.assertEqual(bit_depth, 16, f"Bit depth must be 16-bit PCM, got {bit_depth}")
            self.assertGreaterEqual(duration_sec, 2.9, f"Duration should match requested length, got {duration_sec}")

            sha256 = compute_sha256(test_wav)
            self.assertEqual(len(sha256), 64, "SHA256 hash must be valid 64-character hex string")


if __name__ == "__main__":
    unittest.main()
