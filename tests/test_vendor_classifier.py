import unittest
from src.discovery.vendor_classifier import (
    classify_vendor_from_url,
    classify_vendor_from_html,
)


class TestVendorClassifier(unittest.TestCase):
    def test_classify_vendor_from_urls(self):
        """Tests URL classification for known vendor patterns."""
        self.assertEqual(classify_vendor_from_url("https://events.q4inc.com/attendee/12345"), "Q4 Inc")
        self.assertEqual(classify_vendor_from_url("https://event.notified.com/events/abcde"), "Notified")
        self.assertEqual(classify_vendor_from_url("https://services.choruscall.com/links/xyz.html"), "Nasdaq IR")
        self.assertEqual(classify_vendor_from_url("https://events.zoom.us/w/9988776655"), "Zoom Events")
        self.assertEqual(classify_vendor_from_url("https://event.on24.com/wcc/r/112233"), "ON24")
        self.assertIsNone(classify_vendor_from_url("https://unknown-domain.com/random"))

    def test_classify_vendor_from_html(self):
        """Tests HTML signature detection for vendors embedded in iframes or scripts."""
        html_q4 = """
        <html>
            <body>
                <iframe src="https://events.q4inc.com/webcast/player?id=101"></iframe>
            </body>
        </html>
        """
        vendor, conf = classify_vendor_from_html(html_q4)
        self.assertEqual(vendor, "Q4 Inc")
        self.assertGreaterEqual(conf, 0.85)

        html_custom = """
        <html>
            <body>
                <video src="/media/custom_stream.mp4"></video>
            </body>
        </html>
        """
        vendor_custom, conf_custom = classify_vendor_from_html(html_custom)
        self.assertEqual(vendor_custom, "Custom / In-House")


if __name__ == "__main__":
    unittest.main()
