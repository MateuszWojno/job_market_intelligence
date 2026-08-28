import logging
import time
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

from .config import (
    CHECKPOINT_EVERY,
    DEFAULT_DELAY,
    ERROR_PATH,
    OUTPUT_PATH,
    URLS_PATH,
)
from .driver import create_driver
from .parsers import (
    extract_category,
    extract_company_info,
    extract_contract_type,
    extract_job_locations,
    extract_nice_to_have,
    extract_offer_description,
    extract_offer_details,
    extract_required_skills,
    extract_requirements,
    extract_responsibilities,
    extract_start_date,
    extract_valid_until,
    parse_experience,
    parse_salary,
    parse_workplace,
)
from .storage import (
    load_existing_results,
    load_urls,
    save_errors,
    save_results,
)
from .utils import (
    get_body_text,
    get_job_id,
    get_main_offer_text,
    get_text,
)


class InvalidJobPageError(RuntimeError):
    """Raised when NFJ returns an error/challenge page instead of a job offer."""


INVALID_PAGE_MARKERS = (
    "oferta pracy wygasła",
    "oferta wygasła",
    "ta strona nie działa",
    "jeśli problem nie ustąpi",
    "this site can't be reached",
    "this site can’t be reached",
    "this page isn't working",
    "err_connection",
    "err_name_not_resolved",
    "err_timed_out",
    "err_http2_protocol_error",
    "502 bad gateway",
    "503 service unavailable",
    "504 gateway time-out",
    "access denied",
    "verify you are human",
    "just a moment",
)


def validate_job_page(
    title,
    body_text,
):
    page_text = " ".join(
        value
        for value in (
            title,
            body_text,
        )
        if value
    ).casefold()

    for marker in INVALID_PAGE_MARKERS:
        if marker in page_text:
            raise InvalidJobPageError(
                f"Invalid NFJ page detected: {marker}"
            )

    if not body_text.strip():
        raise InvalidJobPageError(
            "NFJ returned an empty page."
        )


# ============================================================
# SCRAPE ONE JOB
# ============================================================

def scrape_job(
    driver,
    url,
    delay=DEFAULT_DELAY,
):
    driver.get(url)
    time.sleep(delay)

    body_text = get_body_text(
        driver
    )

    main_text = get_main_offer_text(
        body_text
    )

    details_text = extract_offer_details(
        main_text
    )

    title = get_text(
        driver,
        [
            "h1",
            "[data-testid='job-title']",
        ],
    )

    validate_job_page(
        title=title,
        body_text=body_text,
    )

    category = extract_category(
        driver,
        body_text=main_text,
    )

    requirements = extract_requirements(
        main_text
    )

    experience, _ = parse_experience(
        main_text
    )

    _, experience_years_min = (
        parse_experience(
            requirements or ""
        )
    )

    workplace = parse_workplace(
        details_text
    )

    job_locations = extract_job_locations(
        details_text,
        url=url,
    )

    company_info = extract_company_info(
        driver,
        body_text,
    )

    (
        salary_min,
        salary_max,
        salary_currency,
        salary_period,
    ) = parse_salary(main_text)

    contract_type = extract_contract_type(
        main_text
    )

    required_skills = extract_required_skills(
        main_text
    )

    nice_to_have = extract_nice_to_have(
        main_text
    )

    offer_description = extract_offer_description(
        main_text
    )

    responsibilities = extract_responsibilities(
        main_text
    )

    valid_until = extract_valid_until(
        main_text
    )

    start_date = extract_start_date(
        details_text
    )

    scraped_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return {
        "job_id": get_job_id(url),
        "url": url,
        "title": title,
        "category": category,
        "experience": experience,
        "experience_years_min": experience_years_min,
        "workplace": workplace,
        "job_locations": job_locations,
        "company": company_info["company"],
        "company_size": company_info["company_size"],
        "company_founded": company_info["company_founded"],
        "company_locations": company_info["company_locations"],
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": salary_currency,
        "salary_period": salary_period,
        "contract_type": contract_type,
        "required_skills": required_skills,
        "nice_to_have": nice_to_have,
        "requirements": requirements,
        "offer_description": offer_description,
        "responsibilities": responsibilities,
        "valid_until": valid_until,
        "start_date": start_date,
        "scraped_at": scraped_at,
    }


# ============================================================
# MAIN SCRAPER
# ============================================================

def scrape_jobs(
    urls_path=URLS_PATH,
    output_path=OUTPUT_PATH,
    error_path=ERROR_PATH,
    max_jobs=None,
    delay=DEFAULT_DELAY,
    checkpoint_every=CHECKPOINT_EVERY,
    headless=False,
    max_consecutive_page_errors=5,
):
    urls = load_urls(
        urls_path
    )

    if max_jobs is not None:
        urls = urls[:max_jobs]

    logger.info("URLs to check: %d", len(urls))

    results, scraped_urls = (
        load_existing_results(
            output_path
        )
    )

    logger.info("Already scraped: %d", len(scraped_urls))

    driver = create_driver(
        headless=headless
    )

    errors = []
    processed = 0
    consecutive_page_errors = 0

    try:
        for index, url in enumerate(
            urls,
            start=1,
        ):
            if url in scraped_urls:
                continue

            logger.info(
                "Scraping job %d/%d: %s",
                index,
                len(urls),
                url,
            )

            try:
                job = scrape_job(
                    driver=driver,
                    url=url,
                    delay=delay,
                )

                results.append(
                    job
                )

                scraped_urls.add(
                    url
                )

                processed += 1
                consecutive_page_errors = 0

                logger.info(
                    "Scraped job: %s | company=%s | category=%s",
                    job.get("title"),
                    job.get("company"),
                    job.get("category"),
                )

            except InvalidJobPageError as error:
                consecutive_page_errors += 1

                logger.warning("Invalid job page: %s", error)

                errors.append(
                    {
                        "url": url,
                        "error": str(error),
                        "scraped_at":
                            datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                    }
                )

                if (
                    consecutive_page_errors
                    >= max_consecutive_page_errors
                ):
                    logger.error(
                        "Too many invalid NFJ pages in a row. "
                        "Stopping the scraper to protect data quality."
                    )
                    break

            except Exception as error:
                consecutive_page_errors = 0

                logger.exception("Failed to scrape job: %s", url)

                errors.append(
                    {
                        "url": url,
                        "error": str(error),
                        "scraped_at":
                            datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                    }
                )

            if (
                processed > 0
                and processed % checkpoint_every == 0
            ):
                df_checkpoint = save_results(
                    results,
                    output_path,
                )

                save_errors(
                    errors,
                    error_path,
                )

                logger.info(
                    "Checkpoint saved: %d jobs",
                    len(df_checkpoint),
                )

    finally:
        df_final = save_results(
            results,
            output_path,
        )

        save_errors(
            errors,
            error_path,
        )

        driver.quit()

    logger.info(
        "Scraping completed: total=%d | new=%d | errors=%d | output=%s",
        len(df_final),
        processed,
        len(errors),
        output_path,
    )

    return df_final


# ============================================================
# REFRESH MISSING SALARY PERIODS
# ============================================================

def refresh_missing_salary_periods(
    output_path=OUTPUT_PATH,
    error_path=ERROR_PATH,
    max_jobs=None,
    delay=DEFAULT_DELAY,
    checkpoint_every=CHECKPOINT_EVERY,
    headless=False,
):
    """Re-scrape only paid offers whose salary period is missing."""
    results, _ = load_existing_results(
        output_path
    )

    candidates = [
        record
        for record in results
        if pd.isna(record.get("salary_period"))
        and pd.notna(record.get("salary_min"))
        and pd.notna(record.get("salary_max"))
        and pd.notna(record.get("salary_currency"))
        and pd.notna(record.get("url"))
    ]

    if max_jobs is not None:
        candidates = candidates[:max_jobs]

    logger.info(
        "Offers with missing salary period: %d",
        len(candidates),
    )

    if not candidates:
        return pd.DataFrame(results)

    records_by_url = {
        record["url"]: record
        for record in results
        if pd.notna(record.get("url"))
    }
    driver = create_driver(
        headless=headless
    )
    errors = []
    updated = 0
    unresolved = 0

    try:
        for index, record in enumerate(
            candidates,
            start=1,
        ):
            url = record["url"]

            logger.info(
                "Refreshing salary period %d/%d: %s",
                index,
                len(candidates),
                url,
            )

            try:
                refreshed = scrape_job(
                    driver=driver,
                    url=url,
                    delay=delay,
                )

                if refreshed.get("salary_period") is None:
                    unresolved += 1
                    logger.warning(
                        "Salary period is still missing: %s",
                        url,
                    )
                    continue

                target = records_by_url[url]

                for column in (
                    "salary_min",
                    "salary_max",
                    "salary_currency",
                    "salary_period",
                ):
                    target[column] = refreshed.get(column)

                updated += 1
                logger.info(
                    "Salary period updated: %s | period=%s",
                    url,
                    refreshed.get("salary_period"),
                )

            except Exception as error:
                logger.exception(
                    "Failed to refresh salary period: %s",
                    url,
                )
                errors.append(
                    {
                        "url": url,
                        "error": str(error),
                        "scraped_at": datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            if (
                updated > 0
                and updated % checkpoint_every == 0
            ):
                save_results(
                    results,
                    output_path,
                )
                logger.info(
                    "Salary-period checkpoint saved: %d updates",
                    updated,
                )

    finally:
        df_final = save_results(
            results,
            output_path,
        )
        save_errors(
            errors,
            error_path,
        )
        driver.quit()

    logger.info(
        "Salary-period refresh completed: checked=%d | updated=%d | "
        "unresolved=%d | errors=%d | output=%s",
        len(candidates),
        updated,
        unresolved,
        len(errors),
        output_path,
    )

    return df_final


# ============================================================
# REFRESH SELECTED JOBS
# ============================================================

def refresh_job_records(
    urls,
    output_path=OUTPUT_PATH,
    error_path=ERROR_PATH,
    max_jobs=None,
    delay=DEFAULT_DELAY,
    checkpoint_every=CHECKPOINT_EVERY,
    headless=False,
):
    """Replace selected records after a successful fresh scrape."""
    results, _ = load_existing_results(
        output_path
    )

    record_indexes = {
        record["url"]: index
        for index, record in enumerate(results)
        if pd.notna(record.get("url"))
    }

    selected_urls = list(
        dict.fromkeys(
            str(url).strip()
            for url in urls
            if pd.notna(url)
            and str(url).strip() in record_indexes
        )
    )

    if max_jobs is not None:
        selected_urls = selected_urls[:max_jobs]

    logger.info(
        "Selected jobs to refresh: %d",
        len(selected_urls),
    )

    if not selected_urls:
        return pd.DataFrame(results)

    driver = create_driver(
        headless=headless
    )
    errors = []
    updated = 0

    try:
        for index, url in enumerate(
            selected_urls,
            start=1,
        ):
            logger.info(
                "Refreshing selected job %d/%d: %s",
                index,
                len(selected_urls),
                url,
            )

            try:
                refreshed = scrape_job(
                    driver=driver,
                    url=url,
                    delay=delay,
                )

                results[
                    record_indexes[url]
                ] = refreshed
                updated += 1

                logger.info(
                    "Selected job updated: %s | title=%s",
                    url,
                    refreshed.get("title"),
                )

            except Exception as error:
                logger.exception(
                    "Failed to refresh selected job: %s",
                    url,
                )
                errors.append(
                    {
                        "url": url,
                        "error": str(error),
                        "scraped_at": datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    }
                )

            if (
                updated > 0
                and updated % checkpoint_every == 0
            ):
                save_results(
                    results,
                    output_path,
                )
                logger.info(
                    "Selected-job checkpoint saved: %d updates",
                    updated,
                )

    finally:
        df_final = save_results(
            results,
            output_path,
        )
        save_errors(
            errors,
            error_path,
        )
        driver.quit()

    logger.info(
        "Selected-job refresh completed: selected=%d | updated=%d | "
        "errors=%d | output=%s",
        len(selected_urls),
        updated,
        len(errors),
        output_path,
    )

    return df_final


# ============================================================
# TEST ONE JOB
# ============================================================

def scrape_one_job(
    url,
    delay=DEFAULT_DELAY,
    headless=False,
):
    driver = create_driver(
        headless=headless
    )

    try:
        result = scrape_job(
            driver,
            url,
            delay,
        )

    finally:
        driver.quit()

    return result
