import pytest

from nfj.parsers import parse_salary, parse_salary_options


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "130–150 PLN netto (+ VAT) / h B2B",
            (130, 150, "PLN", "hour"),
        ),
        (
            "800 - 1 000 PLN brutto / day",
            (800, 1000, "PLN", "day"),
        ),
        (
            "10 000–13 000 PLN brutto miesięcznie",
            (10000, 13000, "PLN", "month"),
        ),
        (
            "288 000 - 384 000 PLN brutto rocznie (UoP)",
            (288000, 384000, "PLN", "year"),
        ),
        (
            "4 000–5 000 EUR per month",
            (4000, 5000, "EUR", "month"),
        ),
        (
            "90 000 - 110 000 USD annually",
            (90000, 110000, "USD", "year"),
        ),
    ],
)
def test_parse_salary_supported_formats(text, expected):
    assert parse_salary(text) == expected


@pytest.mark.parametrize("text", [None, "", "Salary negotiable"])
def test_parse_salary_returns_empty_result_without_salary_range(text):
    assert parse_salary(text) == (None, None, None, None)


def test_parse_salary_handles_non_breaking_spaces():
    text = "12\xa0000–18\xa0000 PLN miesięcznie"

    assert parse_salary(text) == (12000, 18000, "PLN", "month")


def test_parse_salary_ignores_values_after_salary_section_end_marker():
    text = "Salary negotiable\nAplikuj\n130–150 PLN / h"

    assert parse_salary(text) == (None, None, None, None)


def test_parse_salary_selects_first_complete_option():
    text = (
        "B2B 130–150 PLN / h\n"
        "UoP 20 000–25 000 PLN miesięcznie"
    )

    assert parse_salary(text) == (130, 150, "PLN", "hour")


def test_parse_salary_options_preserves_contract_types():
    text = (
        "B2B 130–150 PLN / h\n"
        "UoP 20 000–25 000 PLN miesięcznie"
    )

    options = parse_salary_options(text)

    assert [option["contract"] for option in options] == ["B2B", "UoP"]
