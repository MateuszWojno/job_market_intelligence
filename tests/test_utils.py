import pytest

from nfj.utils import (
    clean_text,
    get_all_text,
    get_body_text,
    get_job_id,
    get_main_offer_text,
    get_text,
)


class FakeElement:
    def __init__(self, text):
        self.text = text


class FakeDriver:
    def __init__(self, elements_by_selector=None, body_text="", fail=False):
        self.elements_by_selector = elements_by_selector or {}
        self.body_text = body_text
        self.fail = fail

    def find_element(self, by, selector):
        if self.fail:
            raise RuntimeError("driver error")
        return FakeElement(self.body_text)

    def find_elements(self, by, selector):
        if self.fail:
            raise RuntimeError("driver error")
        return self.elements_by_selector.get(selector, [])


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (None, None),
        ("  Python   SQL  ", "Python SQL"),
        ("Python\xa0SQL", "Python SQL"),
        ("Python\nSQL\tDocker", "Python SQL Docker"),
    ],
)
def test_clean_text(text, expected):
    assert clean_text(text) == expected


def test_get_body_text_normalizes_non_breaking_spaces():
    driver = FakeDriver(body_text="  Python\xa0SQL  ")

    assert get_body_text(driver) == "Python SQL"


def test_get_body_text_returns_empty_string_on_driver_error():
    assert get_body_text(FakeDriver(fail=True)) == ""


def test_get_main_offer_text_removes_similar_jobs_footer():
    text = "Main offer\nZOBACZ PODOBNE OFERTY\nOther job"

    assert get_main_offer_text(text) == "Main offer"


def test_get_text_returns_first_non_empty_value():
    driver = FakeDriver(
        elements_by_selector={
            "h1": [FakeElement("  ")],
            "[data-testid='job-title']": [FakeElement(" Data Engineer ")],
        }
    )

    assert get_text(driver, ["h1", "[data-testid='job-title']"]) == (
        "Data Engineer"
    )


def test_get_all_text_collects_clean_values():
    driver = FakeDriver(
        elements_by_selector={
            ".skill": [
                FakeElement(" Python "),
                FakeElement(""),
                FakeElement(" SQL "),
            ]
        }
    )

    assert get_all_text(driver, [".skill"]) == ["Python", "SQL"]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://nofluffjobs.com/pl/job/data-engineer-company-warszawa",
            "data-engineer-company-warszawa",
        ),
        (
            "https://nofluffjobs.com/pl/job/python-developer/",
            "python-developer",
        ),
        (None, None),
    ],
)
def test_get_job_id(url, expected):
    assert get_job_id(url) == expected
