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

    salary_min, salary_max, salary_currency = (
        parse_salary(
            main_text
        )
    )

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
):
    urls = load_urls(
        urls_path
    )

    if max_jobs is not None:
        urls = urls[:max_jobs]

    print(
        f"URLs to check: "
        f"{len(urls)}"
    )

    results, scraped_urls = (
        load_existing_results(
            output_path
        )
    )

    print(
        f"Already downloaded: "
        f"{len(scraped_urls)}"
    )

    driver = create_driver(
        headless=headless
    )

    errors = []
    processed = 0

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

            except Exception as error:
                print(
                    "ERROR:",
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
                    f"Saved: "
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
    print("SCRAPING COMPLETED")
    print("=" * 70)
    print(
        f"Combining offers: "
        f"{len(df_final)}"
    )
    print(
        f"Newly downloaded: "
        f"{processed}"
    )
    print(
        f"Errors: "
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
