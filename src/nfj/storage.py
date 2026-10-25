import os
import tempfile
from pathlib import Path

import pandas as pd

from .config import (
    ERROR_PATH,
    OUTPUT_PATH,
    URLS_PATH,
)


def load_urls(
    urls_path=URLS_PATH,
):
    if not urls_path.exists():
        raise FileNotFoundError(
            f"URL file not found:\n"
            f"{urls_path}\n\n"
            f"Run collect_job_urls() first."
        )

    df = pd.read_csv(
        urls_path
    )

    if "url" not in df.columns:
        raise ValueError(
            "The CSV file must contain "
            "a 'url' column."
        )

    df = df.dropna(
        subset=["url"]
    )

    df["url"] = (
        df["url"]
        .astype(str)
        .str.strip()
    )

    df = df.drop_duplicates(
        subset=["url"]
    )

    return df["url"].tolist()


def load_existing_results(
    output_path=OUTPUT_PATH,
):
    if not output_path.exists():
        return [], set()

    df = pd.read_csv(
        output_path
    )

    if "url" not in df.columns:
        return [], set()

    df = df.drop_duplicates(
        subset=["url"]
    )

    records = df.to_dict(
        "records"
    )

    scraped_urls = set(
        df["url"]
        .dropna()
        .tolist()
    )

    return records, scraped_urls


def atomic_csv(df, output_path):
    """Replace a CSV only after its complete contents have been written."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="",
            dir=output_path.parent, suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            df.to_csv(handle, index=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def save_results(
    results,
    output_path=OUTPUT_PATH,
):
    df = pd.DataFrame(
        results
    )

    if (
        not df.empty
        and "url" in df.columns
    ):
        df = df.drop_duplicates(
            subset=["url"],
            keep="last",
        )

    atomic_csv(df, output_path)

    return df


def save_errors(
    errors,
    error_path=ERROR_PATH,
):
    if not errors:
        return

    df_errors = pd.DataFrame(
        errors
    )

    atomic_csv(df_errors, error_path)
