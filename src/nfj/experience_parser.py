import re

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

