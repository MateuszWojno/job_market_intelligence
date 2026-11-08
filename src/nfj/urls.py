import logging
import time
from pathlib import Path

import pandas as pd
from selenium.webdriver.common.by import By

from .config import (
    CATEGORIES,
    DEFAULT_DELAY,
    URLS_PATH,
)
from .driver import create_driver

logger = logging.getLogger(__name__)

# NFJ cards use camelCase category IDs; listing routes use hyphens.
IT_CARD_CATEGORIES = {slug.replace("-", "") for slug in CATEGORIES}


def collect_job_urls(
    categories=None,
    output_path=URLS_PATH,
    max_pages_per_category=20,
    delay=DEFAULT_DELAY,
    headless=False,
    max_empty_page_retries=2,
    retry_delay=5.0,
):


    if categories is None:
        categories = CATEGORIES

    output_path = Path(output_path)

    driver = create_driver(headless=headless)

    all_urls = set()
    statistics = []

    try:
        for category in categories:
            logger.info("Collecting category: %s", category)

            category_urls = set()
            seen_listing_urls = set()
            global_before = len(all_urls)

            for page in range(
                1,
                max_pages_per_category + 1,
            ):
                url = (
                    f"https://nofluffjobs.com/pl/"
                    f"{category}?page={page}"
                )

                logger.info(
                    "Collecting category page %d: %s",
                    page,
                    url,
                )

                try:
                    page_urls = set()
                    listing_urls = set()

                    for attempt in range(
                        1,
                        max_empty_page_retries + 2,
                    ):
                        driver.get(url)
                        time.sleep(delay)

                        body_text = driver.find_element(By.TAG_NAME, "body").text
                        if "403 ERROR" in body_text and "Request blocked" in body_text:
                            raise RuntimeError(
                                "Server returned 403 Request blocked (CloudFront); "
                                "this is not an empty job listing."
                            )

                        elements = driver.find_elements(
                            By.CSS_SELECTOR,
                            "a.posting-list-item[href*='/job/']",
                        )

                        for element in elements:
                            href = element.get_attribute(
                                "href"
                            )

                            if not href or "/job/" not in href:
                                continue

                            href = (
                                href
                                .split("?")[0]
                                .rstrip("/")
                            )

                            listing_urls.add(href)
                            classes = (element.get_attribute("class") or "").split()
                            for token in classes:
                                if token.startswith("posting-list-item--"):
                                    card_category = token.split("--", 1)[1].lower().replace("-", "")
                                    if card_category in IT_CARD_CATEGORIES:
                                        page_urls.add(href)
                                    break

                        if listing_urls:
                            break

                        if (
                            attempt
                            <= max_empty_page_retries
                        ):
                            logger.warning(
                                "Empty page - retrying in a "
                                "new browser session "
                                f"({attempt}/"
                                f"{max_empty_page_retries})."
                            )
                            driver.quit()
                            time.sleep(retry_delay)
                            driver = create_driver(
                                headless=headless
                            )

                    if not listing_urls:
                        if page == 1:
                            raise RuntimeError(
                                "The first category page remained "
                                "empty after retries. URL collection "
                                "is incomplete."
                            )

                        logger.info(
                            "Empty page after retries - "
                            "treating it as the end of pagination."
                        )
                        break

                    new_category_urls = (
                        page_urls - category_urls
                    )

                    category_urls.update(
                        page_urls
                    )
                    all_urls.update(
                        page_urls
                    )

                    logger.info(
                        "Page collected: urls=%d | new_in_category=%d | "
                        "category_total=%d | global_total=%d",
                        len(page_urls),
                        len(new_category_urls),
                        len(category_urls),
                        len(all_urls),
                    )

                    if listing_urls.issubset(seen_listing_urls):
                        logger.info(
                            "No new offers in category - "
                            "stopping category."
                        )
                        break
                    seen_listing_urls.update(listing_urls)

                except Exception as error:
                    logger.exception(
                        "URL collection failed for category=%s page=%d",
                        category,
                        page,
                    )
                    raise RuntimeError(
                        "URL collection failed. The existing URL "
                        f"file was not overwritten. Cause: {error}"
                    ) from error

            statistics.append(
                {
                    "category": category,
                    "category_urls": len(
                        category_urls
                    ),
                    "new_global_urls": (
                        len(all_urls)
                        - global_before
                    ),
                    "total_urls": len(
                        all_urls
                    ),
                }
            )

    finally:
        driver.quit()

    if not all_urls:
        raise RuntimeError("No verified IT cards collected; the existing URL file was preserved.")

    df_urls = pd.DataFrame(
        {
            "url": sorted(all_urls)
        }
    )

    temporary_path = output_path.with_suffix(
        ".tmp.csv"
    )

    df_urls.to_csv(
        temporary_path,
        index=False,
        encoding="utf-8-sig",
    )

    temporary_path.replace(output_path)

    df_stats = pd.DataFrame(
        statistics
    )

    logger.info(
        "URL collection completed: total_unique_urls=%d | output=%s",
        len(df_urls),
        output_path,
    )
    logger.info(
        "URL collection statistics:\n%s",
        df_stats.to_string(index=False),
    )

    return df_urls, df_stats
