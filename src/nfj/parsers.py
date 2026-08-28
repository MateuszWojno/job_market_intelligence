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

SALARY_PATTERN = (
    r"(\d{1,3}(?:[ \t]+\d{3})+|\d+)"
    r"[ \t]*[–-][ \t]*"
    r"(\d{1,3}(?:[ \t]+\d{3})+|\d+)"
    r"[ \t]*"
    r"(PLN|EUR|USD)"
)


SALARY_PERIOD_PATTERNS = {
    "hour": (
        r"/\s*(?:h|hour)\b|"
        r"\bper\s+hour\b|"
        r"\bhourly\b|"
        r"\b(?:stawka[ \t]+)?godzinowa\b|"
        r"\bgodzinowo\b|"
        r"\bgodz\.?\b"
    ),
    "day": (
        r"/\s*(?:d|day)\b|"
        r"\bper\s+day\b|"
        r"\bdaily\b|"
        r"\b(?:stawka[ \t]+)?dzienna\b|"
        r"\bdziennie\b"
    ),
    "month": (
        r"/\s*(?:m|mo|month|mies|miesiąc)\b|"
        r"\bper\s+month\b|"
        r"\bmonthly\b|"
        r"\bmiesięcz(?:nie|na|ny|nego)?\b|"
        r"\bmiesiecz(?:nie|na|ny|nego)?\b"
    ),
    "year": (
        r"/\s*(?:y|yr|year)\b|"
        r"\bper\s+(?:year|annum)\b|"
        r"\bannual(?:ly)?\b|"
        r"\byearly\b|"
        r"\b(?:rocznie|roczna|roczny|rocznego)\b|"
        r"\bna\s+rok\b"
    ),
}


def extract_salary_period(
    text,
    salary_start,
    salary_end,
    context_before=160,
    context_after=200,
):
    """Return the period marker nearest to a salary range."""
    context_start = max(
        0,
        salary_start - context_before,
    )
    context_end = min(
        len(text),
        salary_end + context_after,
    )
    context = text[
        context_start:context_end
    ]

    salary_center = (
        (salary_start + salary_end) / 2
        - context_start
    )
    candidates = []

    for period, pattern in (
        SALARY_PERIOD_PATTERNS.items()
    ):
        for period_match in re.finditer(
            pattern,
            context,
            re.IGNORECASE,
        ):
            period_center = (
                period_match.start()
                + period_match.end()
            ) / 2
            candidates.append(
                (
                    abs(period_center - salary_center),
                    period_match.start(),
                    period,
                )
            )

    if not candidates:
        return None

    return min(candidates)[2]


def parse_salary(text):

    salary_options = parse_salary_options(text)

    if not salary_options:
        return None, None, None, None

    selected_option = next(
        (
            option
            for option in salary_options
            if option["period"] is not None
        ),
        salary_options[0],
    )

    return (
        selected_option["salary_min"],
        selected_option["salary_max"],
        selected_option["currency"],
        selected_option["period"],
    )


def parse_salary_options(text):

    if not text:
        return []

    text = text.replace("\xa0", " ")

    end_markers = [
        "Szczegóły wynagrodzenia",
        "Aplikuj",
        "Zapisz ofertę",
        "Analiza CV",
        "Oceń tę ofertę",
        "ZOBACZ PODOBNE OFERTY",
    ]

    end_positions = [
        text.lower().find(marker.lower())
        for marker in end_markers
        if text.lower().find(marker.lower()) != -1
    ]

    if end_positions:
        salary_section = text[:min(end_positions)]
    else:
        salary_section = text

    matches = list(
        re.finditer(
            SALARY_PATTERN,
            salary_section,
            re.IGNORECASE
        )
    )


    salary_card_matches = [
        match
        for match in matches
        if len(salary_section) - match.end() <= 800
    ]

    if salary_card_matches:
        matches = salary_card_matches

    salary_options = []

    for i, match in enumerate(matches):
        if i > 0:
            context_start = max(
                matches[i - 1].end(),
                match.start() - 80,
            )
        else:
            context_start = max(
                0,
                match.start() - 80,
            )

        if i + 1 < len(matches):
            context_end = matches[i + 1].start()
        else:
            context_end = min(
                len(salary_section),
                match.end() + 160,
            )

        context = salary_section[
            context_start:context_end
        ]

        salary_min = int(
            re.sub(
                r"[ \t]",
                "",
                match.group(1),
            )
        )

        salary_max = int(
            re.sub(
                r"[ \t]",
                "",
                match.group(2),
            )
        )

        currency = match.group(3).upper()

        # Contract type
        if re.search(
            r"\bB2B\b",
            context,
            re.IGNORECASE
        ):
            contract = "B2B"

        elif re.search(
            r"\bUoP\b",
            context,
            re.IGNORECASE
        ):
            contract = "UoP"

        elif re.search(
            r"\bUZ\b",
            context,
            re.IGNORECASE
        ):
            contract = "UZ"

        else:
            contract = None

        period = extract_salary_period(
            text=context,
            salary_start=(
                match.start() - context_start
            ),
            salary_end=(
                match.end() - context_start
            ),
            context_before=80,
            context_after=160,
        )

        salary_options.append(
            {
                "salary_min": salary_min,
                "salary_max": salary_max,
                "currency": currency,
                "contract": contract,
                "period": period,
            }
        )

    return salary_options


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
# ============================================================

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

    category = clean_text(
        match.group(1).split(",", 1)[0]
    )

    return category or None


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

def _section_heading_pattern(heading):
    return (
        r"^[ \t]*(?:#+[ \t]*)?"
        + re.escape(heading)
        + r"[ \t]*:?[ \t]*$"
    )


def _find_section_heading(
    text,
    heading,
    start=0,
):
    return re.search(
        _section_heading_pattern(heading),
        text[start:],
        re.IGNORECASE | re.MULTILINE,
    )


def _extract_section_text(
    text,
    start_heading,
    end_headings,
    extra_end_patterns=None,
    start_before_heading=None,
):
    if not text:
        return None

    start_match = _find_section_heading(
        text,
        start_heading,
    )

    if not start_match:
        return None

    content_start = start_match.end()

    if start_before_heading:
        boundary_match = _find_section_heading(
            text,
            start_before_heading,
        )

        if (
            boundary_match
            and start_match.start()
            > boundary_match.start()
        ):
            return None

    end_positions = []

    for heading in end_headings:
        end_match = _find_section_heading(
            text,
            heading,
            start=content_start,
        )

        if end_match:
            end_positions.append(
                content_start
                + end_match.start()
            )

    for pattern in extra_end_patterns or []:
        end_match = re.search(
            pattern,
            text[content_start:],
            re.IGNORECASE | re.MULTILINE,
        )

        if end_match:
            end_positions.append(
                content_start
                + end_match.start()
            )

    content_end = (
        min(end_positions)
        if end_positions
        else len(text)
    )

    value = clean_text(
        text[content_start:content_end]
    )

    return value or None


def extract_required_skills(body_text):
    return _extract_section_text(
        text=body_text,
        start_heading="Obowiązkowe",
        end_headings=[
            "Mile widziane",
            "Opis wymagań",
            "Opis oferty",
            "Zakres obowiązków",
            "Szczegóły oferty",
        ],
    )


# ============================================================
# NICE TO HAVE
# ============================================================

def extract_nice_to_have(body_text):
    return _extract_section_text(
        text=body_text,
        start_heading="Mile widziane",
        end_headings=[
            "Opis wymagań",
            "Opis oferty",
        ],
        start_before_heading="Opis wymagań",
    )


# ============================================================
# REQUIREMENTS
# ============================================================

def extract_requirements(body_text):
    return _extract_section_text(
        text=body_text,
        start_heading="Opis wymagań",
        end_headings=[
            "Opis oferty",
            "Zakres obowiązków",
            "Szczegóły oferty",
        ],
    )


# ============================================================
# OFFER DESCRIPTION
# ============================================================

def extract_offer_description(body_text):
    return _extract_section_text(
        text=body_text,
        start_heading="Opis oferty",
        end_headings=[
            "Zakres obowiązków",
            "Szczegóły oferty",
            "O firmie",
        ],
    )


# ============================================================
# RESPONSIBILITIES
# ============================================================

def extract_responsibilities(body_text):
    return _extract_section_text(
        text=body_text,
        start_heading="Zakres obowiązków",
        end_headings=[
            "Opis oferty",
            "Szczegóły oferty",
            "O firmie",
        ],
        extra_end_patterns=[
            r"^[ \t]*pokaż wszystko"
            r"(?:[ \t]*\(\d+\))?"
            r"[ \t]*$",
        ],
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
