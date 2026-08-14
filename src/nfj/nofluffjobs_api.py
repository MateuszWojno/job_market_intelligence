import re
import time
from pathlib import Path
from datetime import datetime

import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

URLS_PATH = DATA_DIR / "nofluff_it_urls.csv"
OUTPUT_PATH = DATA_DIR / "nofluff_it_jobs.csv"
ERROR_PATH = DATA_DIR / "nofluff_scraping_errors.csv"


# ============================================================
# SETTINGS
# ============================================================

DEFAULT_DELAY = 1.0
CHECKPOINT_EVERY = 25


# ============================================================
# NO FLUFF JOBS CATEGORIES
# ============================================================

CATEGORIES = [
    "it",
    "backend",
    "frontend",
    "fullstack",
    "data",
    "ai",
    "devops",
    "security",
    "testing",
    "java",
    ".net",
    "python",
    "mobile",
    "cloud",
    "architecture",
    "business-analysis",
    "project-manager",
    "product-management",
    "support",
    "erp",
    "embedded",
    "qa",
    "ux-ui",
    "blockchain",
    "game",
]


# ============================================================
# SELENIUM
# ============================================================

def create_driver(headless=False):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    return webdriver.Chrome(options=options)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    if text is None:
        return None

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# GET FIRST TEXT
# ============================================================

def get_text(driver, selectors):
    for selector in selectors:
        try:
            elements = driver.find_elements(
                By.CSS_SELECTOR,
                selector,
            )

            for element in elements:
                text = clean_text(element.text)

                if text:
                    return text

        except Exception:
            continue

    return None


# ============================================================
# GET ALL TEXT
# ============================================================

def get_all_text(driver, selectors):
    values = []

    for selector in selectors:
        try:
            elements = driver.find_elements(
                By.CSS_SELECTOR,
                selector,
            )

            for element in elements:
                text = clean_text(element.text)

                if text:
                    values.append(text)

        except Exception:
            continue

    return values


# ============================================================
# JOB ID / SLUG
# ============================================================

def get_job_id(url):
    if not url:
        return None

    try:
        return (
            url
            .rstrip("/")
            .split("/job/")[-1]
        )

    except Exception:
        return None


# ============================================================
# COLLECT JOB URLS
# ============================================================

def collect_job_urls(
    categories=None,
    output_path=URLS_PATH,
    max_pages_per_category=20,
    delay=DEFAULT_DELAY,
    headless=False,
):

    if categories is None:
        categories = CATEGORIES

    driver = create_driver(headless=headless)

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

            for page in range(1, max_pages_per_category + 1):
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
                        href = element.get_attribute("href")

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

                    category_urls.update(page_urls)
                    all_urls.update(page_urls)

                    print(
                        f"URL-i na stronie: {len(page_urls)}"
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
                    "category_urls": len(category_urls),
                    "new_global_urls": (
                        len(all_urls) - global_before
                    ),
                    "total_urls": len(all_urls),
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

    df_stats = pd.DataFrame(statistics)

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



def parse_salary(text):
    if not text:
        return None, None, None

    text = text.replace("\xa0", " ")

    pattern = (
        r"(\d[\d\s]*)"
        r"\s*[–-]\s*"
        r"(\d[\d\s]*)"
        r"\s*"
        r"(PLN|EUR|USD)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE,
    )

    if not match:
        return None, None, None

    try:
        salary_min = int(
            match.group(1).replace(" ", "")
        )

        salary_max = int(
            match.group(2).replace(" ", "")
        )

    except ValueError:
        return None, None, None

    currency = match.group(3).upper()

    return salary_min, salary_max, currency


# ============================================================
# EXPERIENCE
# ============================================================

def parse_experience(text):
    if not text:
        return None, None

    experience = None
    experience_years_min = None

    levels = [
        "Junior",
        "Mid",
        "Senior",
        "Expert",
    ]

    for level in levels:
        if re.search(
            rf"\b{level}\b",
            text,
            re.IGNORECASE,
        ):
            experience = level
            break

    patterns = [
        r"(\d+)\+?\s*lat",
        r"(\d+)\+?\s*roku",
        r"(\d+)\+?\s*years",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            experience_years_min = int(
                match.group(1)
            )
            break

    return experience, experience_years_min


# ============================================================
# WORKPLACE
# ============================================================

def parse_workplace(text):
    if not text:
        return None

    if re.search(
        r"\bPraca zdalna\b|\bRemote\b",
        text,
        re.IGNORECASE,
    ):
        return "Remote"

    if re.search(
        r"\bHybryd",
        text,
        re.IGNORECASE,
    ):
        return "Hybrid"

    if re.search(
        r"\bOnsite\b|\bStacjonarn",
        text,
        re.IGNORECASE,
    ):
        return "Onsite"

    return None


# ============================================================
# COMPANY INFO
# ============================================================

def extract_company_info(
    driver,
    body_text,
):
    company = get_text(
        driver,
        [
            "a[href*='/company/']",
        ],
    )

    company_size = None

    match = re.search(
        r"Wielkość firmy:\s*([^\n]+)",
        body_text,
        re.IGNORECASE,
    )

    if match:
        company_size = clean_text(
            match.group(1)
        )

    company_founded = None

    match = re.search(
        r"Utworzona w:\s*(\d{4})",
        body_text,
        re.IGNORECASE,
    )

    if match:
        company_founded = int(
            match.group(1)
        )

    company_locations = None

    match = re.search(
        r"Lokalizacje:\s*([^\n]+)",
        body_text,
        re.IGNORECASE,
    )

    if match:
        company_locations = clean_text(
            match.group(1)
        )

    return {
        "company": company,
        "company_size": company_size,
        "company_founded": company_founded,
        "company_locations": company_locations,
    }


# ============================================================
# CATEGORY
# ============================================================

def extract_category(driver):
    known_categories = [
        "Fullstack",
        "Backend",
        "Frontend",
        "Data",
        "AI",
        "DevOps",
        "Security",
        "Testing",
        ".NET",
        "Java",
        "Python",
        "Cloud",
        "Mobile",
        "ERP",
        "Support",
        "Architecture",
        "Business Analysis",
        "Project Manager",
        "Product Management",
        "Embedded",
        "UX/UI",
        "Blockchain",
        "Game",
    ]

    elements = get_all_text(
        driver,
        [
            "a[href*='/pl/']",
        ],
    )

    categories = []

    for value in elements:
        for category in known_categories:
            if value.lower() == category.lower():
                categories.append(category)

    categories = list(
        dict.fromkeys(categories)
    )

    if not categories:
        return None

    return ", ".join(categories)


# ============================================================
# JOB LOCATIONS
# ============================================================

def extract_job_locations(body_text):
    if not body_text:
        return None

    patterns = [
        r"Lokalizacja:\s*([^\n]+)",
        r"Location:\s*([^\n]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            body_text,
            re.IGNORECASE,
        )

        if match:
            value = clean_text(
                match.group(1)
            )

            if value:
                return value

    return None


# ============================================================
# CONTRACT TYPE
# ============================================================

def extract_contract_type(body_text):
    if not body_text:
        return None

    contracts = [
        "B2B",
        "Umowa o pracę",
        "Contract of Employment",
        "Umowa zlecenie",
        "Umowa o dzieło",
        "Contract",
    ]

    found = []

    for contract in contracts:
        if re.search(
            re.escape(contract),
            body_text,
            re.IGNORECASE,
        ):
            found.append(contract)

    found = list(
        dict.fromkeys(found)
    )

    if not found:
        return None

    return ", ".join(found)


# ============================================================
# REQUIRED SKILLS
# ============================================================

def extract_required_skills(body_text):
    if not body_text:
        return None

    pattern = (
        r"Obowiązkowe"
        r"(.*?)"
        r"(?:Mile widziane|Opis wymagań)"
    )

    match = re.search(
        pattern,
        body_text,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    return clean_text(
        match.group(1)
    )


# ============================================================
# NICE TO HAVE
# ============================================================

def extract_nice_to_have(body_text):
    if not body_text:
        return None

    pattern = (
        r"Mile widziane"
        r"(.*?)"
        r"(?:Opis wymagań|Opis oferty)"
    )

    match = re.search(
        pattern,
        body_text,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    return clean_text(
        match.group(1)
    )


# ============================================================
# REQUIREMENTS
# ============================================================

def extract_requirements(body_text):
    if not body_text:
        return None

    pattern = (
        r"Opis wymagań"
        r"(.*?)"
        r"(?:Opis oferty|Zakres obowiązków)"
    )

    match = re.search(
        pattern,
        body_text,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    return clean_text(
        match.group(1)
    )


# ============================================================
# OFFER DESCRIPTION
# ============================================================

def extract_offer_description(body_text):
    if not body_text:
        return None

    pattern = (
        r"Opis oferty"
        r"(.*?)"
        r"(?:Zakres obowiązków|Szczegóły oferty)"
    )

    match = re.search(
        pattern,
        body_text,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    return clean_text(
        match.group(1)
    )


# ============================================================
# RESPONSIBILITIES
# ============================================================

def extract_responsibilities(body_text):
    if not body_text:
        return None

    pattern = (
        r"Zakres obowiązków"
        r"(.*?)"
        r"(?:pokaż wszystko|Szczegóły oferty|O firmie)"
    )

    match = re.search(
        pattern,
        body_text,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    return clean_text(
        match.group(1)
    )


# ============================================================
# VALID UNTIL
# ============================================================

def extract_valid_until(body_text):
    if not body_text:
        return None

    match = re.search(
        r"Oferta ważna do:\s*"
        r"(\d{2}\.\d{2}\.\d{4})",
        body_text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)


# ============================================================
# START DATE
# ============================================================

def extract_start_date(body_text):
    if not body_text:
        return None

    match = re.search(
        r"Start\s+([^\n]+)",
        body_text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return clean_text(
        match.group(1)
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

    body_text = get_text(
        driver,
        ["body"],
    )

    if not body_text:
        body_text = ""

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

    experience, experience_years_min = (
        parse_experience(
            body_text
        )
    )

    workplace = parse_workplace(
        body_text
    )

    job_locations = extract_job_locations(
        body_text
    )

    company_info = extract_company_info(
        driver,
        body_text,
    )

    salary_min, salary_max, salary_currency = (
        parse_salary(
            body_text
        )
    )

    contract_type = extract_contract_type(
        body_text
    )

    required_skills = extract_required_skills(
        body_text
    )

    nice_to_have = extract_nice_to_have(
        body_text
    )

    requirements = extract_requirements(
        body_text
    )

    offer_description = extract_offer_description(
        body_text
    )

    responsibilities = extract_responsibilities(
        body_text
    )

    valid_until = extract_valid_until(
        body_text
    )

    start_date = extract_start_date(
        body_text
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
# LOAD URLS
# ============================================================

def load_urls(urls_path=URLS_PATH):
    if not urls_path.exists():
        raise FileNotFoundError(
            f"Nie znaleziono pliku URL-i:\n"
            f"{urls_path}\n\n"
            f"Najpierw uruchom collect_job_urls()."
        )

    df = pd.read_csv(urls_path)

    if "url" not in df.columns:
        raise ValueError(
            "Plik CSV musi zawierać kolumnę 'url'."
        )

    df = df.dropna(
        subset=["url"]
    )

    df["url"] = (
        df["url"]
        .astype(str)
        .str.strip()
    )

    df = df.drop_duplicates(
        subset=["url"]
    )

    return df["url"].tolist()


# ============================================================
# LOAD EXISTING RESULTS
# ============================================================

def load_existing_results(
    output_path=OUTPUT_PATH,
):
    if not output_path.exists():
        return [], set()

    df = pd.read_csv(
        output_path
    )

    if "url" not in df.columns:
        return [], set()

    df = df.drop_duplicates(
        subset=["url"]
    )

    records = df.to_dict(
        "records"
    )

    scraped_urls = set(
        df["url"]
        .dropna()
        .tolist()
    )

    return records, scraped_urls


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(
    results,
    output_path=OUTPUT_PATH,
):
    df = pd.DataFrame(
        results
    )

    if (
        not df.empty
        and "url" in df.columns
    ):
        df = df.drop_duplicates(
            subset=["url"],
            keep="last",
        )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    return df


# ============================================================
# SAVE ERRORS
# ============================================================

def save_errors(
    errors,
    error_path=ERROR_PATH,
):
    if not errors:
        return

    df_errors = pd.DataFrame(
        errors
    )

    df_errors.to_csv(
        error_path,
        index=False,
        encoding="utf-8-sig",
    )


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

                results.append(job)
                scraped_urls.add(url)
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
                    "BŁĄD:",
                    error,
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
                    f"Zapisano: "
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
        f"Łącznie ofert: "
        f"{len(df_final)}"
    )
    print(
        f"Nowo pobranych: "
        f"{processed}"
    )
    print(
        f"Błędów: "
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


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":
    print(
        "Moduł No Fluff Jobs scraper gotowy."
    )

