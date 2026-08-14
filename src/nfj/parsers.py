import json
import re
from urllib.parse import urlparse

from selenium.webdriver.common.by import By

from .utils import (
    clean_text,
    get_all_text,
    get_text,
)


# ============================================================
# HELPERS
# ============================================================

def extract_offer_details(body_text):
    if not body_text:
        return ""

    match = re.search(
        r"Szczegóły oferty\s*"
        r"(.*?)"
        r"(?=\nO firmie|\Z)",
        body_text,
        re.IGNORECASE | re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    return body_text


# ============================================================
# SALARY
# ============================================================

def parse_salary(text):
    if not text:
        return None, None, None

    text = text.replace("\xa0", " ")

    pattern = (
        r"(?<!\d)"
        r"(\d{1,3}(?:[ .]\d{3})*|\d+)"
        r"\s*[–-]\s*"
        r"(\d{1,3}(?:[ .]\d{3})*|\d+)"
        r"\s*"
        r"(PLN|EUR|USD)"
    )

    matches = list(
        re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        )
    )

    if not matches:
        return None, None, None

    for match in reversed(matches):
        try:
            salary_min = int(
                re.sub(
                    r"[ .]",
                    "",
                    match.group(1),
                )
            )

            salary_max = int(
                re.sub(
                    r"[ .]",
                    "",
                    match.group(2),
                )
            )

        except ValueError:
            continue

        if salary_min > salary_max:
            continue

        currency = (
            match.group(3)
            .upper()
        )

        return (
            salary_min,
            salary_max,
            currency,
        )

    return None, None, None


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

    # Najpierw zakresy: "7-10 lat" -> 7
    range_patterns = [
        r"(\d+)\s*[–-]\s*(\d+)\s*(?:lat|lata|years?)",
        r"(\d+)\s*to\s*(\d+)\s*years?",
    ]

    for pattern in range_patterns:
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

    # Jeśli nie ma zakresu, szukamy wartości minimalnej.
    if experience_years_min is None:
        patterns = [
            r"(?:min(?:imum)?\.?\s*)?(\d+)\+?\s*(?:lat|lata|rok|roku)",
            r"(?:min(?:imum)?\.?\s*)?(\d+)\+?\s*years?",
            r"(?:min(?:imum)?\.?\s*)?(\d+)[-\s]*(?:letnie|letnia|letnim|letni)\s+doświadczenie",
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

    return (
        experience,
        experience_years_min,
    )


# ============================================================
# WORKPLACE
# ============================================================

def parse_workplace(text):
    if not text:
        return None

    # Hybryda musi być sprawdzana przed Remote.
    if re.search(
        r"Hybryd|"
        r"Praca zdalna przez\s+\d+\s+dni?|"
        r"Praca zdalna:\s*Elastyczna|"
        r"\bHybrid\b",
        text,
        re.IGNORECASE,
    ):
        return "Hybrid"

    if re.search(
        r"Praca w pełni zdalna|"
        r"100%\s*(?:praca\s*)?zdalna|"
        r"\bFully remote\b|"
        r"\bRemote\b",
        text,
        re.IGNORECASE,
    ):
        return "Remote"

    if re.search(
        r"\bOnsite\b|"
        r"\bOn-site\b|"
        r"\bStacjonarn",
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
    company = None

    title = get_text(
        driver,
        [
            "h1",
            "[data-testid='job-title']",
        ],
    )

    def normalize_value(value):
        if not value:
            return ""

        value = clean_text(value)

        return re.sub(
            r"[^a-z0-9ąćęłńóśźż]+",
            "",
            value.casefold(),
        )

    normalized_title = normalize_value(
        title
    )

    def valid_company_candidate(value):
        if not value:
            return False

        value = clean_text(value)
        normalized = normalize_value(
            value
        )

        if not normalized:
            return False

        # Najważniejsza poprawka:
        # tytuł oferty NIE może zostać firmą.
        if normalized == normalized_title:
            return False

        blocked = {
            "junior",
            "mid",
            "senior",
            "expert",
            "remote",
            "hybrid",
            "onsite",
            "zdalnie",
            "hybrydowo",
            "stacjonarnie",
            "data",
            "backend",
            "frontend",
            "fullstack",
            "devops",
            "security",
            "testing",
        }

        if value.casefold() in blocked:
            return False

        if value.casefold().startswith(
            (
                "kategoria",
                "category",
                "lokalizacja",
                "lokalizacje",
                "location",
                "oferta ważna do",
            )
        ):
            return False

        if re.search(
            r"\d[\d\s.]*\s*[–-]\s*\d",
            value,
        ):
            return False

        return True

    # --------------------------------------------------------
    # 1. Kandydaci z DOM
    # --------------------------------------------------------

    selectors = [
        "[data-testid='company-name']",
        "a[href*='/company/']",
    ]

    for selector in selectors:
        try:
            elements = driver.find_elements(
                By.CSS_SELECTOR,
                selector,
            )

            for element in elements:
                candidate = clean_text(
                    element.text
                )

                if valid_company_candidate(
                    candidate
                ):
                    company = candidate
                    break

            if company:
                break

        except Exception:
            continue

    # --------------------------------------------------------
    # 2. JSON-LD
    # --------------------------------------------------------

    def find_hiring_organization_name(obj):
        if isinstance(obj, dict):
            organization = obj.get(
                "hiringOrganization"
            )

            if isinstance(
                organization,
                dict,
            ):
                name = organization.get(
                    "name"
                )

                if valid_company_candidate(
                    name
                ):
                    return clean_text(
                        name
                    )

            for value in obj.values():
                result = (
                    find_hiring_organization_name(
                        value
                    )
                )

                if result:
                    return result

        elif isinstance(obj, list):
            for item in obj:
                result = (
                    find_hiring_organization_name(
                        item
                    )
                )

                if result:
                    return result

        return None

    if not company:
        try:
            scripts = driver.find_elements(
                By.CSS_SELECTOR,
                "script[type='application/ld+json']",
            )

            for script in scripts:
                raw_json = script.get_attribute(
                    "innerHTML"
                )

                if not raw_json:
                    continue

                try:
                    data = json.loads(
                        raw_json
                    )

                except Exception:
                    continue

                company = (
                    find_hiring_organization_name(
                        data
                    )
                )

                if company:
                    break

        except Exception:
            pass

    # --------------------------------------------------------
    # 3. Nagłówek strony
    # --------------------------------------------------------

    if not company and body_text:
        lines = [
            clean_text(line)
            for line in body_text.splitlines()
            if clean_text(line)
        ]

        title_indexes = [
            index
            for index, line in enumerate(lines)
            if normalize_value(line)
            == normalized_title
        ]

        for title_index in title_indexes:
            for candidate in lines[
                title_index + 1:
                title_index + 10
            ]:
                # Gdy dotarliśmy do kategorii,
                # firma powinna już być wcześniej.
                if candidate.casefold().startswith(
                    (
                        "kategoria",
                        "category",
                    )
                ):
                    break

                if valid_company_candidate(
                    candidate
                ):
                    company = candidate
                    break

            if company:
                break

    # --------------------------------------------------------
    # 4. Sekcja O firmie
    # --------------------------------------------------------

    if not company:
        patterns = [
            (
                r"(?:^|\n)"
                r"O firmie\s*\n\s*"
                r"([^\n]+)"
            ),
            (
                r"(?:^|\n)"
                r"O firmie\s+"
                r"(.+?)"
                r"(?=\s+Utworzona w:|"
                r"\s+Wielkość firmy:|"
                r"\s+Siedziba:|"
                r"\s+Lokalizacje:|"
                r"\n|\Z)"
            ),
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                body_text,
                re.IGNORECASE,
            )

            if match:
                candidate = clean_text(
                    match.group(1)
                )

                if valid_company_candidate(
                    candidate
                ):
                    company = candidate
                    break

    # --------------------------------------------------------
    # COMPANY SIZE
    # --------------------------------------------------------

    company_size = None

    match = re.search(
        r"(?:^|\n)"
        r"Wielkość firmy:\s*"
        r"([^\n]+)",
        body_text,
        re.IGNORECASE,
    )

    if match:
        company_size = clean_text(
            match.group(1)
        )

    # --------------------------------------------------------
    # COMPANY FOUNDED
    # --------------------------------------------------------

    company_founded = None

    match = re.search(
        r"(?:^|\n)"
        r"Utworzona w:\s*"
        r"(\d{4})",
        body_text,
        re.IGNORECASE,
    )

    if match:
        company_founded = int(
            match.group(1)
        )

    # --------------------------------------------------------
    # COMPANY LOCATIONS
    # --------------------------------------------------------

    company_locations = None

    match = re.search(
        r"(?:^|\n)"
        r"Lokalizacje:\s*"
        r"([^\n]+)",
        body_text,
        re.IGNORECASE,
    )

    if match:
        company_locations = clean_text(
            match.group(1)
        )

    else:
        match = re.search(
            r"(?:^|\n)"
            r"Siedziba:\s*"
            r"([^\n]+)",
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
                categories.append(
                    category
                )

    categories = list(
        dict.fromkeys(
            categories
        )
    )

    if not categories:
        return None

    return ", ".join(
        categories
    )


# ============================================================
# JOB LOCATIONS
# ============================================================

CITY_SLUGS = {
    "warszawa": "Warszawa",
    "warsaw": "Warszawa",
    "krakow": "Kraków",
    "cracow": "Kraków",
    "gdansk": "Gdańsk",
    "gdynia": "Gdynia",
    "sopot": "Sopot",
    "wroclaw": "Wrocław",
    "poznan": "Poznań",
    "lodz": "Łódź",
    "katowice": "Katowice",
    "gliwice": "Gliwice",
    "bydgoszcz": "Bydgoszcz",
    "torun": "Toruń",
    "szczecin": "Szczecin",
    "lublin": "Lublin",
    "rzeszow": "Rzeszów",
    "bialystok": "Białystok",
    "olsztyn": "Olsztyn",
    "opole": "Opole",
    "kielce": "Kielce",
    "zielona-gora": "Zielona Góra",
    "gorzow-wielkopolski": "Gorzów Wielkopolski",
    "bielsko-biala": "Bielsko-Biała",
    "czestochowa": "Częstochowa",
    "radom": "Radom",
    "tychy": "Tychy",
}


def extract_job_locations(
    text,
    url=None,
):
    if text:
        patterns = [
            r"(?:^|\n)Lokalizacja:\s*([^\n]+)",
            r"(?:^|\n)Location:\s*([^\n]+)",
            r"(?:^|\n)Miejsce pracy:\s*([^\n]+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if match:
                value = clean_text(
                    match.group(1)
                )

                if value:
                    return value

    # Fallback z URL-a
    if url:
        try:
            slug = (
                urlparse(url)
                .path
                .rstrip("/")
                .split("/")[-1]
                .lower()
            )

            for city_slug, city_name in sorted(
                CITY_SLUGS.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            ):
                if re.search(
                    rf"(?:^|-){re.escape(city_slug)}(?:-|$)",
                    slug,
                ):
                    return city_name

        except Exception:
            pass

    return None


# ============================================================
# CONTRACT TYPE
# ============================================================

def extract_contract_type(text):
    if not text:
        return None

    contract_patterns = [
        (
            "B2B",
            r"\bB2B\b",
        ),
        (
            "Umowa o pracę",
            r"Umowa o pracę|"
            r"Contract of Employment|"
            r"Employment Contract",
        ),
        (
            "Umowa zlecenie",
            r"Umowa zlecenie",
        ),
        (
            "Umowa o dzieło",
            r"Umowa o dzieło",
        ),
    ]

    found = []

    for label, pattern in contract_patterns:
        if re.search(
            pattern,
            text,
            re.IGNORECASE,
        ):
            found.append(
                label
            )

    found = list(
        dict.fromkeys(
            found
        )
    )

    if not found:
        return None

    return ", ".join(
        found
    )


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
        r"(?:pokaż wszystko|"
        r"Szczegóły oferty|O firmie)"
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

def extract_start_date(text):
    if not text:
        return None

    match = re.search(
        r"(?:^|\n)"
        r"Start\s*:?\s*"
        r"([^\n]+)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    return clean_text(
        match.group(1)
    )
