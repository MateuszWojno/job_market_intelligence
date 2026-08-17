import time
from datetime import datetime

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
        driver
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
    ) = parse_salary(body_text)

    # Szukamy w całej głównej ofercie, nie tylko
    # w sekcji "Szczegóły oferty".
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

    print(
        f"URL-i do sprawdzenia: "
        f"{len(urls)}"
    )

    results, scraped_urls = (
        load_existing_results(
            output_path
        )
    )

    print(

        f"Już pobranych: "
        f"Already scraped: "
        (Modified scraper.py)
        f"{len(scraped_urls)}"
    )

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

            print()
            print("=" * 70)
            print(
                f"[{index}/{len(urls)}]"
            )
            print(url)

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

                print(
                    "OK:",
                    job.get("title"),
                )
                print(
                    "Company:",
                    job.get("company"),
                )
                print(
                    "Category:",
                    job.get("category"),
                )

            except InvalidJobPageError as error:
                consecutive_page_errors += 1

                print(
                    "PAGE ERROR:",
                    error,
                )

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
                    print()
                    print(
                        "Too many invalid NFJ pages in a row. "
                        "Stopping the scraper to protect data quality."
                    )
                    break

            except Exception as error:
                consecutive_page_errors = 0

                print(
                    "BŁĄD:",
                    error,
                )

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

                print()
                print("CHECKPOINT")
                print(

                    f"Saved jobs: "
                (Modified scraper.py)
                    f"{len(df_checkpoint)}"
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

    print()
    print("=" * 70)
    print("SCRAPING ZAKOŃCZONY")
    print("=" * 70)
    print(

        f"Total jobs: "
        f"{len(df_final)}"
    )
    print(
        f"Newly scraped: "
        f"{processed}"
    )
    print(
        f"Errors in this run: "
          (Modified scraper.py)
        f"{len(errors)}"
    )
    print()
    print("CSV:")
    print(output_path)

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
