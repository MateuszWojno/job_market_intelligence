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
    """
    Pobiera unikalne URL-e ofert z kategorii No Fluff Jobs
    i zapisuje je do CSV.
    """

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
            print(f"KATEGORIA: {category}")
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
                print(f"Strona {page}:")
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
                        f"URL-i na stronie: "
                        f"{len(page_urls)}"
                    )
                    print(
                        f"Nowych w kategorii: "
                        f"{len(new_category_urls)}"
                    )
                    print(
                        f"Unikalnych w kategorii: "
                        f"{len(category_urls)}"
                    )
                    print(
                        f"Łącznie globalnie: "
                        f"{len(all_urls)}"
                    )

                    if not new_category_urls:
                        print(
                            "Brak nowych ofert w kategorii - "
                            "zatrzymuję kategorię."
                        )
                        break

                except Exception as error:
                    print(
                        f"Błąd strony {page}: {error}"
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
    print("ZBIERANIE URL-I ZAKOŃCZONE")
    print("=" * 70)
    print(
        f"Łącznie unikalnych URL-i: "
        f"{len(df_urls)}"
    )
    print()
    print("Statystyki:")
    print(df_stats)
    print()
    print("Zapisano URL-e:")
    print(output_path)

    return df_urls, df_stats
