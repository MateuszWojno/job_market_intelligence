import logging
from datetime import datetime

import pandas as pd

from .config import CHECKPOINT_EVERY, DEFAULT_DELAY, ERROR_PATH, OUTPUT_PATH
from .driver import create_driver
from .job_scraper import scrape_job
from .storage import load_existing_results, save_errors, save_results

logger = logging.getLogger(__name__)


def refresh_missing_salary_periods(
    output_path=OUTPUT_PATH, error_path=ERROR_PATH, max_jobs=None,
    delay=DEFAULT_DELAY, checkpoint_every=CHECKPOINT_EVERY, headless=False,
):
    """Re-scrape only paid offers whose salary period is missing."""
    results, _ = load_existing_results(output_path)
    candidates = [
        record for record in results
        if pd.isna(record.get("salary_period"))
        and pd.notna(record.get("salary_min"))
        and pd.notna(record.get("salary_max"))
        and pd.notna(record.get("salary_currency"))
        and pd.notna(record.get("url"))
    ]
    if max_jobs is not None:
        candidates = candidates[:max_jobs]
    logger.info("Offers with missing salary period: %d", len(candidates))
    if not candidates:
        return pd.DataFrame(results)

    records_by_url = {
        record["url"]: record for record in results
        if pd.notna(record.get("url"))
    }
    driver = create_driver(headless=headless)
    errors = []
    updated = 0
    unresolved = 0

    try:
        for index, record in enumerate(candidates, start=1):
            url = record["url"]
            logger.info("Refreshing salary period %d/%d: %s", index, len(candidates), url)
            try:
                refreshed = scrape_job(driver=driver, url=url, delay=delay)
                if refreshed.get("salary_period") is None:
                    unresolved += 1
                    logger.warning("Salary period is still missing: %s", url)
                    continue
                target = records_by_url[url]
                for column in ("salary_min", "salary_max", "salary_currency", "salary_period"):
                    target[column] = refreshed.get(column)
                updated += 1
                logger.info("Salary period updated: %s | period=%s", url, refreshed.get("salary_period"))
            except Exception as error:
                logger.exception("Failed to refresh salary period: %s", url)
                errors.append(_error_record(url, error))

            if updated > 0 and updated % checkpoint_every == 0:
                save_results(results, output_path)
                logger.info("Salary-period checkpoint saved: %d updates", updated)
    finally:
        df_final = save_results(results, output_path)
        save_errors(errors, error_path)
        driver.quit()

    logger.info(
        "Salary-period refresh completed: checked=%d | updated=%d | unresolved=%d | errors=%d | output=%s",
        len(candidates), updated, unresolved, len(errors), output_path,
    )
    return df_final


def refresh_job_records(
    urls, output_path=OUTPUT_PATH, error_path=ERROR_PATH, max_jobs=None,
    delay=DEFAULT_DELAY, checkpoint_every=CHECKPOINT_EVERY, headless=False,
):
    """Replace selected records after a successful fresh scrape."""
    results, _ = load_existing_results(output_path)
    record_indexes = {
        record["url"]: index for index, record in enumerate(results)
        if pd.notna(record.get("url"))
    }
    selected_urls = list(dict.fromkeys(
        str(url).strip() for url in urls
        if pd.notna(url) and str(url).strip() in record_indexes
    ))
    if max_jobs is not None:
        selected_urls = selected_urls[:max_jobs]
    logger.info("Selected jobs to refresh: %d", len(selected_urls))
    if not selected_urls:
        return pd.DataFrame(results)

    driver = create_driver(headless=headless)
    errors = []
    updated = 0

    try:
        for index, url in enumerate(selected_urls, start=1):
            logger.info("Refreshing selected job %d/%d: %s", index, len(selected_urls), url)
            try:
                refreshed = scrape_job(driver=driver, url=url, delay=delay)
                results[record_indexes[url]] = refreshed
                updated += 1
                logger.info("Selected job updated: %s | title=%s", url, refreshed.get("title"))
            except Exception as error:
                logger.exception("Failed to refresh selected job: %s", url)
                errors.append(_error_record(url, error))

            if updated > 0 and updated % checkpoint_every == 0:
                save_results(results, output_path)
                logger.info("Selected-job checkpoint saved: %d updates", updated)
    finally:
        df_final = save_results(results, output_path)
        save_errors(errors, error_path)
        driver.quit()

    logger.info(
        "Selected-job refresh completed: selected=%d | updated=%d | errors=%d | output=%s",
        len(selected_urls), updated, len(errors), output_path,
    )
    return df_final


def _error_record(url, error):
    return {
        "url": url,
        "error": str(error),
        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
