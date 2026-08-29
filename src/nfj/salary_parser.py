import re


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

