import pandas as pd

import nfj.refresh as module


class FakeDriver:
    def __init__(self):
        self.quit_called = False

    def quit(self):
        self.quit_called = True


def configure_refresh(monkeypatch, records):
    driver = FakeDriver()
    saved_errors = []
    monkeypatch.setattr(module, "load_existing_results", lambda path: (records, set()))
    monkeypatch.setattr(module, "create_driver", lambda headless: driver)
    monkeypatch.setattr(module, "save_results", lambda rows, path: pd.DataFrame(rows))
    monkeypatch.setattr(
        module, "save_errors", lambda errors, path: saved_errors.append(errors.copy())
    )
    return driver, saved_errors


def test_refresh_missing_salary_periods_updates_only_eligible_records(monkeypatch, tmp_path):
    records = [
        {"url": "eligible", "salary_min": 100, "salary_max": 150, "salary_currency": "PLN", "salary_period": None},
        {"url": "no-salary", "salary_min": None, "salary_max": None, "salary_currency": None, "salary_period": None},
        {"url": "complete", "salary_min": 10000, "salary_max": 15000, "salary_currency": "PLN", "salary_period": "month"},
    ]
    driver, errors = configure_refresh(monkeypatch, records)
    calls = []

    def scrape(driver, url, delay):
        calls.append(url)
        return {"salary_min": 100, "salary_max": 150, "salary_currency": "PLN", "salary_period": "hour"}

    monkeypatch.setattr(module, "scrape_job", scrape)
    result = module.refresh_missing_salary_periods(
        output_path=tmp_path / "jobs.csv",
        error_path=tmp_path / "errors.csv",
        delay=0,
    )

    assert calls == ["eligible"]
    assert result.loc[result["url"] == "eligible", "salary_period"].item() == "hour"
    assert errors[-1] == []
    assert driver.quit_called


def test_refresh_missing_salary_periods_keeps_unresolved_value(monkeypatch, tmp_path):
    records = [{"url": "a", "salary_min": 100, "salary_max": 150, "salary_currency": "PLN", "salary_period": None}]
    driver, errors = configure_refresh(monkeypatch, records)
    monkeypatch.setattr(module, "scrape_job", lambda **kwargs: {"salary_period": None})

    result = module.refresh_missing_salary_periods(
        output_path=tmp_path / "jobs.csv", error_path=tmp_path / "errors.csv", delay=0
    )

    assert pd.isna(result.loc[0, "salary_period"])
    assert driver.quit_called


def test_refresh_job_records_deduplicates_selection_and_replaces_record(monkeypatch, tmp_path):
    records = [{"url": "a", "title": "Old"}, {"url": "b", "title": "Keep"}]
    driver, errors = configure_refresh(monkeypatch, records)
    calls = []

    def scrape(driver, url, delay):
        calls.append(url)
        return {"url": url, "title": "New"}

    monkeypatch.setattr(module, "scrape_job", scrape)
    result = module.refresh_job_records(
        ["a", "a", "missing"],
        output_path=tmp_path / "jobs.csv",
        error_path=tmp_path / "errors.csv",
        delay=0,
    )

    assert calls == ["a"]
    assert result.set_index("url").loc["a", "title"] == "New"
    assert result.set_index("url").loc["b", "title"] == "Keep"
    assert driver.quit_called


def test_refresh_job_records_preserves_record_after_error(monkeypatch, tmp_path):
    records = [{"url": "a", "title": "Old"}]
    driver, errors = configure_refresh(monkeypatch, records)

    def fail(**kwargs):
        raise RuntimeError("failure")

    monkeypatch.setattr(module, "scrape_job", fail)
    result = module.refresh_job_records(
        ["a"], output_path=tmp_path / "jobs.csv", error_path=tmp_path / "errors.csv", delay=0
    )

    assert result.loc[0, "title"] == "Old"
    assert errors[-1][0]["url"] == "a"
    assert driver.quit_called
