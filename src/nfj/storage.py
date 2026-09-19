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

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

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

    df_errors.to_csv(
        error_path,
        index=False,
        encoding="utf-8-sig",
    )
