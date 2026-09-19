import pandas as pd
import pytest

from nfj.storage import (
    load_existing_results,
    load_urls,
    save_errors,
    save_results,
)


def test_load_urls_cleans_missing_whitespace_and_duplicates(tmp_path):
    path = tmp_path / "urls.csv"
    pd.DataFrame({"url": [" a ", "a", None, "b"]}).to_csv(path, index=False)

    assert load_urls(path) == ["a", "b"]


def test_load_urls_rejects_missing_file_and_url_column(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_urls(tmp_path / "missing.csv")

    path = tmp_path / "invalid.csv"
    pd.DataFrame({"link": ["a"]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="url"):
        load_urls(path)


def test_load_existing_results_handles_missing_and_invalid_file(tmp_path):
    assert load_existing_results(tmp_path / "missing.csv") == ([], set())

    path = tmp_path / "invalid.csv"
    pd.DataFrame({"title": ["Developer"]}).to_csv(path, index=False)
    assert load_existing_results(path) == ([], set())


def test_save_and_load_results_keep_latest_duplicate(tmp_path):
    path = tmp_path / "jobs.csv"
    saved = save_results(
        [
            {"url": "a", "title": "Old"},
            {"url": "b", "title": "Other"},
            {"url": "a", "title": "New"},
        ],
        path,
    )
    records, urls = load_existing_results(path)

    assert len(saved) == 2
    assert urls == {"a", "b"}
    assert {row["url"]: row["title"] for row in records}["a"] == "New"


def test_save_errors_writes_only_nonempty_collection(tmp_path):
    path = tmp_path / "errors.csv"
    save_errors([], path)
    assert not path.exists()

    save_errors([{"url": "a", "error": "failure"}], path)
    assert pd.read_csv(path).to_dict("records") == [
        {"url": "a", "error": "failure"}
    ]
