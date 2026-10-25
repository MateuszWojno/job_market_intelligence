import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from nfj import storage

spec = importlib.util.spec_from_file_location(
    "collect_weekly", Path(__file__).resolve().parents[1] / "tools" / "collect_weekly.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(name):
    return {"job_id": name, "url": name, "scraped_at": "2026-10-25 10:00:00"}


class WeeklyCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "jobs.csv"
        self.urls = self.root / "urls.csv"
        self.artifacts = self.root / "artifacts"
        self.paths = (self.output, self.urls, self.artifacts)
        pd.DataFrame([record("old")]).to_csv(self.output, index=False)

    def collect(self, urls):
        def fake(**kwargs):
            self.assertTrue(kwargs["headless"])
            self.assertGreaterEqual(kwargs["delay"], 3)
            frame = pd.DataFrame({"url": urls})
            frame.to_csv(kwargs["output_path"], index=False)
            return frame, pd.DataFrame({"category": ["data"]})
        return fake

    def summary(self):
        return json.loads(next(self.artifacts.glob("runs/*/summary.json")).read_text())

    def test_success_preserves_old_and_adds_new(self):
        with patch.object(module, "collect_job_urls", self.collect(["old", "new"])), patch.object(
            module, "scrape_jobs", return_value=pd.DataFrame([record("old"), record("new")])
        ):
            self.assertEqual(module.run_collection(*self.paths), 0)
        self.assertEqual(pd.read_csv(self.output)["job_id"].tolist(), ["old", "new"])
        self.assertEqual(self.summary()["new_records"], 1)
        self.assertEqual(self.summary()["status"], "complete")

    def test_partial_run_reports_missing_urls(self):
        with patch.object(module, "collect_job_urls", self.collect(["old", "new", "failed"])), patch.object(
            module, "scrape_jobs", return_value=pd.DataFrame([record("old"), record("new")])
        ):
            self.assertEqual(module.run_collection(*self.paths), 2)
        self.assertEqual(self.summary()["status"], "partial")
        self.assertEqual(self.summary()["urls_without_record"], 1)

    def test_invalid_results_leave_original_unchanged(self):
        original = self.output.read_bytes()
        with patch.object(module, "collect_job_urls", self.collect(["old", "new"])), patch.object(
            module, "scrape_jobs", return_value=pd.DataFrame([record("old"), record("old")])
        ):
            self.assertEqual(module.run_collection(*self.paths), 1)
        self.assertEqual(self.output.read_bytes(), original)
        self.assertEqual(self.summary()["status"], "failed")

    def test_no_new_urls_skips_details(self):
        with patch.object(module, "collect_job_urls", self.collect(["old"])), patch.object(module, "scrape_jobs") as scrape:
            self.assertEqual(module.run_collection(*self.paths), 0)
            scrape.assert_not_called()
        self.assertEqual(self.summary()["new_records"], 0)

    def test_collection_failure_leaves_original_unchanged(self):
        original = self.output.read_bytes()
        with patch.object(module, "collect_job_urls", side_effect=RuntimeError("Network unavailable")):
            self.assertEqual(module.run_collection(*self.paths), 1)
        self.assertEqual(self.output.read_bytes(), original)

    def test_failed_atomic_replace_preserves_original(self):
        original = self.output.read_bytes()
        with patch.object(storage.os, "replace", side_effect=OSError("File locked")):
            with self.assertRaises(OSError):
                storage.atomic_csv(pd.DataFrame([record("new")]), self.output)
        self.assertEqual(self.output.read_bytes(), original)
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_save_results_retains_latest_duplicate(self):
        storage.save_results([record("old"), record("new"), record("old")], self.output)
        self.assertEqual(pd.read_csv(self.output)["job_id"].tolist(), ["new", "old"])

    def test_lock_blocks_second_collector_and_releases(self):
        lock = self.artifacts / "collection.lock"
        with module.collection_lock(lock):
            with self.assertRaises(RuntimeError):
                with module.collection_lock(lock):
                    self.fail("Concurrent lock was acquired")
        with module.collection_lock(lock):
            pass
