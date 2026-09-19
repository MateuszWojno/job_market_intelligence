from types import SimpleNamespace

from nfj.job_details_parser import (
    extract_category,
    extract_contract_type,
    extract_offer_details,
    extract_start_date,
    extract_valid_until,
)


class FakeDriver:
    def __init__(self, elements=None, raises=False):
        self.elements = elements or []
        self.raises = raises

    def find_elements(self, by, selector):
        if self.raises:
            raise RuntimeError("DOM unavailable")
        return self.elements


def test_extract_category_prefers_dom():
    driver = FakeDriver([SimpleNamespace(text=" Data ")])
    assert extract_category(driver, "Kategoria:\nBackend") == "Data"


def test_extract_category_falls_back_to_text():
    driver = FakeDriver(raises=True)
    assert extract_category(driver, "Category:\nBackend, Fullstack") == "Backend"


def test_extract_category_returns_none_without_value():
    assert extract_category(FakeDriver(), "Plain offer") is None


def test_extract_contract_type_supports_multiple_contracts():
    text = "We offer B2B or Contract of Employment."
    assert extract_contract_type(text) == "B2B, Umowa o pracę"


def test_extract_contract_type_returns_none_for_missing_information():
    assert extract_contract_type("No contract details") is None


def test_offer_details_and_dates():
    body = "Header\nSzczegóły oferty\nStart: ASAP\nOferta ważna do: 31.12.2026\nO firmie\nACME"
    details = extract_offer_details(body)

    assert extract_start_date(details) == "ASAP"
    assert extract_valid_until(details) == "31.12.2026"
