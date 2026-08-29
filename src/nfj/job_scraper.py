import time
from datetime import datetime

from .config import DEFAULT_DELAY
from .driver import create_driver
from .parsers import (
    extract_category, extract_company_info, extract_contract_type,
    extract_job_locations, extract_nice_to_have, extract_offer_description,
    extract_offer_details, extract_required_skills, extract_requirements,
    extract_responsibilities, extract_start_date, extract_valid_until,
    parse_experience, parse_salary, parse_workplace,
)
from .utils import get_body_text, get_job_id, get_main_offer_text, get_text


class InvalidJobPageError(RuntimeError):
    """Raised when NFJ returns an error/challenge page instead of a job offer."""


INVALID_PAGE_MARKERS = (
    "oferta pracy wygasła", "oferta wygasła", "ta strona nie działa",
    "jeśli problem nie ustąpi", "this site can't be reached",
    "this site can’t be reached", "this page isn't working",
    "err_connection", "err_name_not_resolved", "err_timed_out",
    "err_http2_protocol_error", "502 bad gateway", "503 service unavailable",
    "504 gateway time-out", "access denied", "verify you are human",
    "just a moment",
)


def validate_job_page(title, body_text):
    page_text = " ".join(value for value in (title, body_text) if value).casefold()
    for marker in INVALID_PAGE_MARKERS:
        if marker in page_text:
            raise InvalidJobPageError(f"Invalid NFJ page detected: {marker}")
    if not body_text.strip():
        raise InvalidJobPageError("NFJ returned an empty page.")


def scrape_job(driver, url, delay=DEFAULT_DELAY):
    """Scrape and parse one job page using an existing browser driver."""
    driver.get(url)
    time.sleep(delay)
    body_text = get_body_text(driver)
    main_text = get_main_offer_text(body_text)
    details_text = extract_offer_details(main_text)
    title = get_text(driver, ["h1", "[data-testid='job-title']"])
    validate_job_page(title=title, body_text=body_text)

    category = extract_category(driver, body_text=main_text)
    requirements = extract_requirements(main_text)
    experience, _ = parse_experience(main_text)
    _, experience_years_min = parse_experience(requirements or "")
    workplace = parse_workplace(details_text)
    job_locations = extract_job_locations(details_text, url=url)
    company_info = extract_company_info(driver, body_text)
    salary_min, salary_max, salary_currency, salary_period = parse_salary(main_text)
    contract_type = extract_contract_type(main_text)
    required_skills = extract_required_skills(main_text)
    nice_to_have = extract_nice_to_have(main_text)
    offer_description = extract_offer_description(main_text)
    responsibilities = extract_responsibilities(main_text)
    valid_until = extract_valid_until(main_text)
    start_date = extract_start_date(details_text)
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "job_id": get_job_id(url), "url": url, "title": title,
        "category": category, "experience": experience,
        "experience_years_min": experience_years_min, "workplace": workplace,
        "job_locations": job_locations, "company": company_info["company"],
        "company_size": company_info["company_size"],
        "company_founded": company_info["company_founded"],
        "company_locations": company_info["company_locations"],
        "salary_min": salary_min, "salary_max": salary_max,
        "salary_currency": salary_currency, "salary_period": salary_period,
        "contract_type": contract_type, "required_skills": required_skills,
        "nice_to_have": nice_to_have, "requirements": requirements,
        "offer_description": offer_description,
        "responsibilities": responsibilities, "valid_until": valid_until,
        "start_date": start_date, "scraped_at": scraped_at,
    }


def scrape_one_job(url, delay=DEFAULT_DELAY, headless=False):
    """Create a temporary driver and scrape a single job offer."""
    driver = create_driver(headless=headless)
    try:
        return scrape_job(driver, url, delay)
    finally:
        driver.quit()
