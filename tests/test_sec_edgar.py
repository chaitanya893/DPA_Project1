import unittest
from src.discovery.sec_edgar import clean_cik, extract_earnings_event_from_8k


class TestSecEdgar(unittest.TestCase):
    def test_clean_cik(self):
        """Tests zero-padding of CIK strings to 10 characters."""
        self.assertEqual(clean_cik("320193"), "0000320193")
        self.assertEqual(clean_cik("0000789019"), "0000789019")
        self.assertEqual(clean_cik("CIK12345"), "0000012345")

    def test_extract_earnings_event_from_8k(self):
        """Tests parsing 8-K submissions metadata into a structured event."""
        mock_submissions = {
            "filings": {
                "recent": {
                    "form": ["10-Q", "8-K", "DEF 14A"],
                    "accessionNumber": ["0001-01-01", "0000320193-24-000050", "0001-01-03"],
                    "filingDate": ["2024-05-01", "2024-08-01", "2024-03-01"],
                    "primaryDocument": ["doc1.htm", "aapl-20240801.htm", "doc3.htm"],
                    "items": ["", "2.02", ""],
                }
            }
        }

        event = extract_earnings_event_from_8k("0000320193", mock_submissions)
        self.assertIsNotNone(event)
        self.assertEqual(event["fiscal_period"], "Q3 FY2024")
        self.assertEqual(event["discovery_source"], "SEC_EDGAR_8K_ITEM_2.02")
        self.assertIn("aapl-20240801.htm", event["doc_url"])


if __name__ == "__main__":
    unittest.main()
