import re

from selenium.webdriver.common.by import By

from .utils import clean_text

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

def extract_category(
    driver,
    body_text=None,
):
    try:
        elements = driver.find_elements(
            By.XPATH,
            "//*[normalize-space()='Kategoria:' "
            "or normalize-space()='Category:']"
            "/following::a[normalize-space()][1]",
        )

        for element in elements:
            category = clean_text(
                element.text
            )

            if category:
                return category

    except Exception:
        pass

    if not body_text:
        return None

    match = re.search(
        r"(?:^|\n)[ \t]*"
        r"(?:Kategoria|Category):[ \t]*"
        r"(?:\r?\n)+[ \t]*"
        r"([^\r\n]+)",
        body_text,
        re.IGNORECASE,
    )

    if not match:
        return None

    category = clean_text(match.group(1).split(",", 1)[0])

    return category or None

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
