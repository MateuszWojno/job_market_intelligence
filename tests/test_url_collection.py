import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from nfj.urls import collect_job_urls


class UrlCollectionTests(unittest.TestCase):
    def test_mixed_results_only_queue_verified_it_cards(self):
        def card(slug, category):
            element = Mock()
            element.get_attribute.side_effect = {
                "href": "https://nofluffjobs.com/pl/job/" + slug,
                "class": "posting-list-item posting-list-item--" + category,
            }.get
            return element

        driver = Mock()
        driver.find_element.return_value.text = "Znalezione oferty pracy"
        driver.find_elements.side_effect = [
            [card("recruiter-it", "hr"), card("engineer", "finance")],
            [card("analyst", "businessIntelligence"), card("buyer", "logistics")],
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "urls.csv"
            with patch("nfj.urls.create_driver", return_value=driver), patch("nfj.urls.time.sleep"):
                urls, _ = collect_job_urls(categories=["data"], output_path=output, max_pages_per_category=2)
            self.assertEqual(urls["url"].tolist(), ["https://nofluffjobs.com/pl/job/analyst"])
            self.assertNotIn("recruiter", output.read_text(encoding="utf-8-sig"))

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
