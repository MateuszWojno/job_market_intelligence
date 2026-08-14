import time

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
):


    if categories is None:
        categories = CATEGORIES

    driver = create_driver(
        headless=headless
    )

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
                    driver.get(url)
                    time.sleep(delay)

                    elements = driver.find_elements(
                        By.CSS_SELECTOR,
                        "a[href*='/job/']",
                    )

                    page_urls = set()

                    for element in elements:
                        href = element.get_attribute(
                            "href"
                        )

                        if not href:
                            continue

                        if "/job/" not in href:
                            continue

                        href = (
                            href
                            .split("?")[0]
                            .rstrip("/")
                        )

                        page_urls.add(href)

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
                    break

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

    df_urls.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

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
