import json

from nfj.company_parser import extract_company_info


class FakeElement:
    def __init__(self, text="", inner_html=None):
        self.text = text
        self.inner_html = inner_html

    def get_attribute(self, name):
        return self.inner_html if name == "innerHTML" else None


class FakeDriver:
    def __init__(self, responses=None):
        self.responses = responses or {}

    def find_elements(self, by, selector):
        return self.responses.get(selector, [])


def test_extract_company_info_from_dom():
    driver = FakeDriver({
        "h1": [FakeElement("Data Engineer")],
        "[data-testid='company-name']": [FakeElement("Example Tech")],
    })

    result = extract_company_info(
        driver,
        "Wielkość firmy: 250 - 499\nUtworzona w: 2012\nLokalizacje: Warszawa, Kraków",
    )

    assert result == {
        "company": "Example Tech",
        "company_size": "250 - 499",
        "company_founded": 2012,
        "company_locations": "Warszawa, Kraków",
    }


def test_extract_company_info_falls_back_to_json_ld():
    data = {"hiringOrganization": {"name": "JSON Company"}}
    driver = FakeDriver({
        "h1": [FakeElement("Python Developer")],
        "script[type='application/ld+json']": [
            FakeElement(inner_html=json.dumps(data))
        ],
    })

    result = extract_company_info(driver, "Offer body")

    assert result["company"] == "JSON Company"


def test_extract_company_info_falls_back_to_page_header():
    driver = FakeDriver({"h1": [FakeElement("Data Analyst")]})
    body = "Data Analyst\nHeader Company\nKategoria:\nData"

    assert extract_company_info(driver, body)["company"] == "Header Company"


def test_extract_company_info_rejects_profile_label_and_uses_company_section():
    driver = FakeDriver({
        "h1": [FakeElement("Data Analyst")],
        "[data-testid='company-name']": [FakeElement("Zobacz profil firmy")],
    })
    body = "O firmie\nActual Company\nSiedziba: Gdańsk"

    result = extract_company_info(driver, body)

    assert result["company"] == "Actual Company"
    assert result["company_locations"] == "Gdańsk"


def test_extract_company_info_handles_invalid_json_ld():
    driver = FakeDriver({
        "h1": [FakeElement("Developer")],
        "script[type='application/ld+json']": [FakeElement(inner_html="{")],
    })

    assert extract_company_info(driver, "Plain body")["company"] is None
