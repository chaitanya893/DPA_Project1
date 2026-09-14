import csv
import os
import unittest
from config.settings import UNIVERSE_CSV_PATH


class TestUniverse(unittest.TestCase):
    def test_universe_csv_exists_and_has_25_companies(self):
        """Validates that universe.csv exists, has exactly 25 companies, and meets all category requirements."""
        self.assertTrue(os.path.exists(UNIVERSE_CSV_PATH), "universe.csv file must exist in config directory")

        with open(UNIVERSE_CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        self.assertEqual(len(reader), 25, f"Expected exactly 25 companies, got {len(reader)}")

        # Required columns
        expected_headers = [
            "company_name",
            "ticker",
            "exchange",
            "country",
            "cik_or_sedar_id",
            "ir_page_url",
            "market_cap_bucket",
            "expected_call_language",
        ]
        for header in expected_headers:
            self.assertIn(header, reader[0], f"Missing required column: {header}")

        # Category validation
        us_large = [r for r in reader if r["country"] == "US" and r["market_cap_bucket"] == "large_cap"]
        us_small = [r for r in reader if r["country"] == "US" and r["market_cap_bucket"] == "small_cap"]
        ca_tsx = [r for r in reader if r["country"] == "CA" and r["expected_call_language"] == "en"]
        ca_french_bilingual = [r for r in reader if r["country"] == "CA" and "fr" in r["expected_call_language"]]

        self.assertEqual(len(us_large), 10, f"Expected 10 US Large Cap, got {len(us_large)}")
        self.assertEqual(len(us_small), 5, f"Expected 5 US Small Cap, got {len(us_small)}")
        self.assertEqual(len(ca_tsx), 7, f"Expected 7 TSX Canadian English, got {len(ca_tsx)}")
        self.assertEqual(len(ca_french_bilingual), 3, f"Expected 3 Canadian French/Bilingual, got {len(ca_french_bilingual)}")


if __name__ == "__main__":
    unittest.main()
