import re

from .utils import clean_text

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

