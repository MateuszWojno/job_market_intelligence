import pytest

from nfj.parsers import parse_experience


@pytest.mark.parametrize(
    ("text", "expected_level"),
    [
        ("Junior Python Developer", "Junior"),
        ("Mid Java Engineer", "Mid"),
        ("Senior Data Engineer", "Senior"),
        ("Expert Cloud Architect", "Expert"),
        ("SENIOR backend developer", "Senior"),
    ],
)
def test_parse_experience_levels(text, expected_level):
    level, _ = parse_experience(text)

    assert level == expected_level


@pytest.mark.parametrize(
    ("text", "expected_years"),
    [
        ("Wymagane 3-5 lat doświadczenia", 3),
        ("At least 4 to 6 years of experience", 4),
        ("Minimum 5 years of experience", 5),
        ("Min. 2 lata doświadczenia", 2),
        ("3-letnie doświadczenie komercyjne", 3),
    ],
)
def test_parse_experience_minimum_years(text, expected_years):
    _, years = parse_experience(text)

    assert years == expected_years


@pytest.mark.parametrize("text", [None, "", "Experience is welcome"])
def test_parse_experience_returns_empty_result_without_match(text):
    assert parse_experience(text) == (None, None)


def test_parse_experience_returns_level_and_years_together():
    assert parse_experience("Senior role requiring 5+ years") == (
        "Senior",
        5,
    )
