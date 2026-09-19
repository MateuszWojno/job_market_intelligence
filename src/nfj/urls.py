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

                    for attempt in range(
                        1,
                        max_empty_page_retries + 2,
                    ):
                        driver.get(url)
                        time.sleep(delay)

                        elements = driver.find_elements(
                            By.CSS_SELECTOR,
                            "a[href*='/job/']",
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

                            page_urls.add(href)

                        if page_urls:
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

                    if not page_urls:
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

                    if not new_category_urls:
                        logger.info(
                            "No new offers in category - "
                            "stopping category."
                        )
                        break

                except Exception as error:
                    logger.exception(
                        "URL collection failed for category=%s page=%d",
                        category,
                        page,
                    )
                    raise RuntimeError(
                        "URL collection failed. The existing URL "
                        "file was not overwritten."
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
