import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from nfj.urls import collect_job_urls


class UrlCollectionTests(unittest.TestCase):
    def test_blocked_response_preserves_urls_and_stops_without_retry(self):
        driver = Mock()
        driver.find_element.return_value.text = "403 ERROR Request blocked. CloudFront"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "urls.csv"
            original = b"url\nhttps://example.com/job/old\n"
            output.write_bytes(original)
            with patch("nfj.urls.create_driver", return_value=driver) as create, \
                    patch("nfj.urls.time.sleep"):
                with self.assertRaisesRegex(RuntimeError, "403 Request blocked"):
                    collect_job_urls(categories=["it"], output_path=output)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(create.call_count, 1)
            driver.quit.assert_called_once()
            driver.find_elements.assert_not_called()
