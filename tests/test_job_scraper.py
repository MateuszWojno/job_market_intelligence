import pytest

import nfj.job_scraper as module
from nfj.job_scraper import InvalidJobPageError, validate_job_page


class FakeDriver:
    def __init__(self):
        self.visited = []
        self.quit_called = False

    def get(self, url):
        self.visited.append(url)

    def quit(self):
        self.quit_called = True


@pytest.mark.parametrize(
    "text",
    ["Oferta pracy wygasła", "503 Service Unavailable", "Verify you are human"],
)
def test_validate_job_page_rejects_invalid_pages(text):
    with pytest.raises(InvalidJobPageError):
        validate_job_page("Title", text)


def test_validate_job_page_rejects_empty_body():
    with pytest.raises(InvalidJobPageError, match="empty"):
        validate_job_page("Title", "")


def test_scrape_job_builds_complete_record(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr(module.time, "sleep", lambda delay: None)
    monkeypatch.setattr(module, "get_body_text", lambda driver: "BODY")
    monkeypatch.setattr(module, "get_main_offer_text", lambda text: "MAIN")
    monkeypatch.setattr(module, "extract_offer_details", lambda text: "DETAILS")
    monkeypatch.setattr(module, "get_text", lambda driver, selectors: "Data Engineer")
    monkeypatch.setattr(module, "extract_category", lambda driver, body_text: "Data")
    monkeypatch.setattr(module, "extract_requirements", lambda text: "3 years")

    def fake_experience(text):
        return ("Senior", None) if text == "MAIN" else (None, 3)

    monkeypatch.setattr(module, "parse_experience", fake_experience)
    monkeypatch.setattr(module, "parse_workplace", lambda text: "Remote")
    monkeypatch.setattr(module, "extract_job_locations", lambda text, url: "Warszawa")
    monkeypatch.setattr(module, "extract_company_info", lambda driver, text: {
        "company": "ACME", "company_size": "100+",
        "company_founded": 2010, "company_locations": "Warszawa",
    })
    monkeypatch.setattr(module, "parse_salary", lambda text: (100, 150, "PLN", "hour"))
    monkeypatch.setattr(module, "extract_contract_type", lambda text: "B2B")
    monkeypatch.setattr(module, "extract_required_skills", lambda text: "Python SQL")
    monkeypatch.setattr(module, "extract_nice_to_have", lambda text: "Docker")
    monkeypatch.setattr(module, "extract_offer_description", lambda text: "Description")
    monkeypatch.setattr(module, "extract_responsibilities", lambda text: "Build pipelines")
    monkeypatch.setattr(module, "extract_valid_until", lambda text: "31.12.2026")
    monkeypatch.setattr(module, "extract_start_date", lambda text: "ASAP")

    result = module.scrape_job(driver, "https://site/job/data-engineer", delay=0)

    assert driver.visited == ["https://site/job/data-engineer"]
    assert result["job_id"] == "data-engineer"
    assert result["company"] == "ACME"
    assert result["experience_years_min"] == 3
    assert result["salary_period"] == "hour"
    assert len(result) == 25


def test_scrape_one_job_always_closes_driver(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr(module, "create_driver", lambda headless: driver)
    monkeypatch.setattr(module, "scrape_job", lambda driver, url, delay: {"url": url})

    assert module.scrape_one_job("url", delay=0, headless=True) == {"url": "url"}
    assert driver.quit_called


def test_scrape_one_job_closes_driver_after_error(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr(module, "create_driver", lambda headless: driver)

    def fail(*args):
        raise RuntimeError("failure")

    monkeypatch.setattr(module, "scrape_job", fail)

    with pytest.raises(RuntimeError, match="failure"):
        module.scrape_one_job("url", delay=0)
    assert driver.quit_called
