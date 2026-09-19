import logging
from datetime import datetime

from .config import CHECKPOINT_EVERY, DEFAULT_DELAY, ERROR_PATH, OUTPUT_PATH, URLS_PATH
from .driver import create_driver
from .job_scraper import InvalidJobPageError, scrape_job
from .storage import load_existing_results, load_urls, save_errors, save_results

logger = logging.getLogger(__name__)


def scrape_jobs(
    urls_path=URLS_PATH, output_path=OUTPUT_PATH, error_path=ERROR_PATH,
    max_jobs=None, delay=DEFAULT_DELAY, checkpoint_every=CHECKPOINT_EVERY,
    headless=False, max_consecutive_page_errors=5,
):
    """Scrape job URLs incrementally and persist checkpoints and errors."""
    urls = load_urls(urls_path)
    if max_jobs is not None:
        urls = urls[:max_jobs]
    logger.info("URLs to check: %d", len(urls))
    results, scraped_urls = load_existing_results(output_path)
    logger.info("Already scraped: %d", len(scraped_urls))
    driver = create_driver(headless=headless)
    errors = []
    processed = 0
    consecutive_page_errors = 0

    try:
        for index, url in enumerate(urls, start=1):
            if url in scraped_urls:
                continue
            logger.info("Scraping job %d/%d: %s", index, len(urls), url)
            try:
                job = scrape_job(driver=driver, url=url, delay=delay)
                results.append(job)
                scraped_urls.add(url)
                processed += 1
                consecutive_page_errors = 0
                logger.info("Scraped job: %s | company=%s | category=%s", job.get("title"), job.get("company"), job.get("category"))
            except InvalidJobPageError as error:
                consecutive_page_errors += 1
                logger.warning("Invalid job page: %s", error)
                errors.append(_error_record(url, error))
                if consecutive_page_errors >= max_consecutive_page_errors:
                    logger.error("Too many invalid NFJ pages in a row. Stopping the scraper to protect data quality.")
                    break
            except Exception as error:
                consecutive_page_errors = 0
                logger.exception("Failed to scrape job: %s", url)
                errors.append(_error_record(url, error))

            if processed > 0 and processed % checkpoint_every == 0:
                df_checkpoint = save_results(results, output_path)
                save_errors(errors, error_path)
                logger.info("Checkpoint saved: %d jobs", len(df_checkpoint))
    finally:
        df_final = save_results(results, output_path)
        save_errors(errors, error_path)
        driver.quit()

    logger.info("Scraping completed: total=%d | new=%d | errors=%d | output=%s", len(df_final), processed, len(errors), output_path)
    return df_final


def _error_record(url, error):
    return {"url": url, "error": str(error), "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
