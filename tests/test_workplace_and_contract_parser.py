import pytest

from nfj.parsers import extract_contract_type, parse_workplace


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Praca hybrydowa", "Hybrid"),
        ("Hybrid work model", "Hybrid"),
        ("Praca zdalna przez 3 dni", "Hybrid"),
        ("100% praca zdalna", "Remote"),
        ("Fully remote position", "Remote"),
        ("Praca stacjonarna", "Onsite"),
        ("On-site role", "Onsite"),
    ],
)
def test_parse_workplace_supported_models(text, expected):
    assert parse_workplace(text) == expected


def test_parse_workplace_prioritizes_hybrid_over_remote_wording():
    assert parse_workplace("Hybrid role with remote days") == "Hybrid"


@pytest.mark.parametrize("text", [None, "", "Flexible workplace"])
def test_parse_workplace_returns_none_without_match(text):
    assert parse_workplace(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("B2B", "B2B"),
        ("Umowa o pracę", "Umowa o pracę"),
        ("Employment Contract", "Umowa o pracę"),
        ("Umowa zlecenie", "Umowa zlecenie"),
        ("Umowa o dzieło", "Umowa o dzieło"),
        ("B2B lub Umowa o pracę", "B2B, Umowa o pracę"),
    ],
)
def test_extract_contract_type_supported_contracts(text, expected):
    assert extract_contract_type(text) == expected


@pytest.mark.parametrize("text", [None, "", "Contract details unavailable"])
def test_extract_contract_type_returns_none_without_match(text):
    assert extract_contract_type(text) is None
