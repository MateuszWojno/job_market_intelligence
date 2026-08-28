import pytest

from nfj.parsers import extract_job_locations


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Lokalizacja: Warszawa", "Warszawa"),
        ("Location: Kraków", "Kraków"),
        ("Miejsce pracy:  Gdańsk  ", "Gdańsk"),
        ("Details\nLokalizacja: Wrocław\nStart: ASAP", "Wrocław"),
    ],
)
def test_extract_job_locations_from_offer_text(text, expected):
    assert extract_job_locations(text) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://nofluffjobs.com/pl/job/data-engineer-warsaw", "Warszawa"),
        ("https://nofluffjobs.com/pl/job/python-developer-cracow", "Kraków"),
        ("https://nofluffjobs.com/pl/job/devops-gdansk-1", "Gdańsk"),
        (
            "https://nofluffjobs.com/pl/job/backend-gorzow-wielkopolski",
            "Gorzów Wielkopolski",
        ),
    ],
)
def test_extract_job_locations_from_url_fallback(url, expected):
    assert extract_job_locations(None, url=url) == expected


def test_extract_job_locations_prefers_text_over_url():
    result = extract_job_locations(
        "Lokalizacja: Łódź",
        url="https://nofluffjobs.com/pl/job/developer-warszawa",
    )

    assert result == "Łódź"


@pytest.mark.parametrize(
    ("text", "url"),
    [(None, None), ("", "https://nofluffjobs.com/pl/job/remote-role")],
)
def test_extract_job_locations_returns_none_without_city(text, url):
    assert extract_job_locations(text, url=url) is None
