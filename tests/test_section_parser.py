from nfj.parsers import (
    extract_nice_to_have,
    extract_offer_description,
    extract_offer_details,
    extract_required_skills,
    extract_requirements,
    extract_responsibilities,
    extract_start_date,
    extract_valid_until,
)


OFFER_TEXT = """
Obowiązkowe
Python
SQL
Mile widziane
Docker
Opis wymagań
Minimum 3 lata doświadczenia.
Opis oferty
Projekt dla sektora finansowego.
Zakres obowiązków
Budowanie potoków danych.
Monitorowanie jakości danych.
Szczegóły oferty
Start: ASAP
O firmie
Example Company
"""


def test_extract_required_skills_stops_at_next_heading():
    assert extract_required_skills(OFFER_TEXT) == "Python SQL"


def test_extract_nice_to_have_stops_at_requirements():
    assert extract_nice_to_have(OFFER_TEXT) == "Docker"


def test_extract_requirements_stops_at_offer_description():
    assert extract_requirements(OFFER_TEXT) == (
        "Minimum 3 lata doświadczenia."
    )


def test_extract_offer_description_stops_at_responsibilities():
    assert extract_offer_description(OFFER_TEXT) == (
        "Projekt dla sektora finansowego."
    )


def test_extract_responsibilities_stops_at_offer_details():
    assert extract_responsibilities(OFFER_TEXT) == (
        "Budowanie potoków danych. Monitorowanie jakości danych."
    )


def test_extract_responsibilities_stops_at_show_all_marker():
    text = """
Zakres obowiązków
First responsibility
Pokaż wszystko (5)
Unrelated footer
"""

    assert extract_responsibilities(text) == "First responsibility"


def test_extract_nice_to_have_rejects_heading_after_requirements():
    text = """
Opis wymagań
Python
Mile widziane
Docker
"""

    assert extract_nice_to_have(text) is None


def test_section_extractors_return_none_without_heading():
    text = "Plain offer text without structured headings"

    assert extract_required_skills(text) is None
    assert extract_requirements(text) is None
    assert extract_offer_description(text) is None
    assert extract_responsibilities(text) is None


def test_extract_offer_details_returns_only_details_section():
    text = """
Header
Szczegóły oferty
Start: ASAP
Lokalizacja: Warszawa
O firmie
Example Company
"""

    assert extract_offer_details(text) == (
        "Start: ASAP\nLokalizacja: Warszawa"
    )


def test_extract_offer_details_returns_original_text_without_heading():
    text = "Unstructured offer details"

    assert extract_offer_details(text) == text


def test_extract_valid_until():
    assert extract_valid_until("Oferta ważna do: 31.12.2026") == (
        "31.12.2026"
    )


def test_extract_valid_until_returns_none_without_date():
    assert extract_valid_until("Apply today") is None


def test_extract_start_date_for_asap_and_explicit_date():
    assert extract_start_date("Start: ASAP") == "ASAP"
    assert extract_start_date("Details\nStart: 2026-09-01") == "2026-09-01"


def test_extract_start_date_returns_none_without_start_heading():
    assert extract_start_date("Available immediately") is None
