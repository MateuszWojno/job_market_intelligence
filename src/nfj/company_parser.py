import json
import re

from selenium.webdriver.common.by import By

from .utils import clean_text, get_text

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
            "zobaczprofilfirmy",
            "zobaczprofilpracodawcy",
            "viewcompanyprofile",
            "companyprofile",
            "ofirmie",
            "aboutcompany",
            "aplikuj",
            "apply",
        }

        if normalized in blocked:
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
    # 1. CANDIDATES FROM DOM
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
    # 3. PAGE HEADER
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
    # 4. COMPANY SECTION
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

