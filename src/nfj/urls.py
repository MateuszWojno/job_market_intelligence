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
            print()
            print("=" * 70)
            print(f"Category: {category}")
            print("=" * 70)

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

                print()
                print(f"Page {page}:")
                print(url)

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
                            print(
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

                        print(
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

                    print(
                        f"URL-i on page: "
                        f"{len(page_urls)}"
                    )
                    print(
                        f"New in category: "
                        f"{len(new_category_urls)}"
                    )
                    print(
                        "Unique in category: "
                        f"{len(category_urls)}"
                    )
                    print(
                        f"Total globally: "
                        f"{len(all_urls)}"
                    )

                    if not new_category_urls:
                        print(
                            "No new offers in category - "
                            "stopping category."
                        )
                        break

                except Exception as error:
                    print(
                        f"Page {page} error: {error}"
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

    print()
    print("=" * 70)
    print("URL COLLECTION COMPLETED")
    print("=" * 70)
    print(
        f"Total unique URLs: "
        f"{len(df_urls)}"
    )
    print()
    print("Statistics:")
    print(df_stats)
    print()
    print("Saved URLs:")
    print(output_path)

    return df_urls, df_stats
