import pandas as pd

import nfj.pipeline as module
from nfj.job_scraper import InvalidJobPageError


class FakeDriver:
    def __init__(self):
        self.quit_called = False

    def quit(self):
        self.quit_called = True


def configure_pipeline(monkeypatch, urls, existing=None):
    driver = FakeDriver()
    saved_results = []
    saved_errors = []
    existing = existing or []
    monkeypatch.setattr(module, "load_urls", lambda path: urls)
    monkeypatch.setattr(
        module,
        "load_existing_results",
        lambda path: (existing.copy(), {row["url"] for row in existing}),
    )
    monkeypatch.setattr(module, "create_driver", lambda headless: driver)

    def save_results(results, path):
        saved_results.append([row.copy() for row in results])
        return pd.DataFrame(results)

    monkeypatch.setattr(module, "save_results", save_results)
    monkeypatch.setattr(
        module, "save_errors", lambda errors, path: saved_errors.append(errors.copy())
    )
    return driver, saved_results, saved_errors


def test_scrape_jobs_skips_existing_urls_and_saves_checkpoint(monkeypatch, tmp_path):
    existing = [{"url": "old", "title": "Existing"}]
    driver, saved_results, saved_errors = configure_pipeline(
        monkeypatch, ["old", "new"], existing
    )
    calls = []

    def scrape(driver, url, delay):
        calls.append(url)
        return {"url": url, "title": "New", "company": "ACME", "category": "Data"}

    monkeypatch.setattr(module, "scrape_job", scrape)
    result = module.scrape_jobs(
        urls_path=tmp_path / "urls.csv",
        output_path=tmp_path / "jobs.csv",
        error_path=tmp_path / "errors.csv",
        delay=0,
        checkpoint_every=1,
    )

    assert calls == ["new"]
    assert len(result) == 2
    assert len(saved_results) == 2
    assert saved_errors[-1] == []
    assert driver.quit_called


def test_scrape_jobs_records_regular_error_and_continues(monkeypatch, tmp_path):
    driver, saved_results, saved_errors = configure_pipeline(monkeypatch, ["bad", "good"])

    def scrape(driver, url, delay):
        if url == "bad":
            raise RuntimeError("network")
        return {"url": url, "title": "Good", "company": None, "category": None}

    monkeypatch.setattr(module, "scrape_job", scrape)
    result = module.scrape_jobs(
        urls_path=tmp_path / "urls.csv",
        output_path=tmp_path / "jobs.csv",
        error_path=tmp_path / "errors.csv",
        delay=0,
    )

    assert result["url"].tolist() == ["good"]
    assert saved_errors[-1][0]["url"] == "bad"
    assert driver.quit_called


def test_scrape_jobs_stops_after_consecutive_invalid_pages(monkeypatch, tmp_path):
    driver, saved_results, saved_errors = configure_pipeline(
        monkeypatch, ["bad-1", "bad-2", "not-reached"]
    )
    calls = []

    def scrape(driver, url, delay):
        calls.append(url)
        raise InvalidJobPageError("expired")

    monkeypatch.setattr(module, "scrape_job", scrape)
    module.scrape_jobs(
        urls_path=tmp_path / "urls.csv",
        output_path=tmp_path / "jobs.csv",
        error_path=tmp_path / "errors.csv",
        delay=0,
        max_consecutive_page_errors=2,
    )

    assert calls == ["bad-1", "bad-2"]
    assert len(saved_errors[-1]) == 2
    assert driver.quit_called
