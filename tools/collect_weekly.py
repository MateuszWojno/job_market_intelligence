"""Unattended incremental collection. Does not clean data or write to PostgreSQL."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfj.config import OUTPUT_PATH, URLS_PATH
from nfj.pipeline import scrape_jobs
from nfj.storage import atomic_csv
from nfj.urls import collect_job_urls
import pandas as pd

LOGGER = logging.getLogger(__name__)


@contextmanager
def collection_lock(path):
    """OS lock is released even if the process is killed; the file may remain."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise RuntimeError("Another scheduled collection is running.") from error
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise RuntimeError("Another scheduled collection is running.") from error
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def validate_records(frame):
    if frame.empty:
        raise ValueError("Collection contains no records.")
    for column in ("job_id", "url", "scraped_at"):
        if column not in frame or frame[column].isna().any():
            raise ValueError(f"Missing values or column: {column}")
        if frame[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Empty values: {column}")
    if not frame["job_id"].is_unique or not frame["url"].is_unique:
        raise ValueError("Duplicate job IDs or URLs.")
    pd.to_datetime(frame["scraped_at"], errors="raise")


def run_collection(output_path=OUTPUT_PATH, urls_path=URLS_PATH,
                   artifact_dir=ROOT / "artifacts" / "collection", delay=3.0):
    output_path, urls_path, artifact_dir = map(Path, (output_path, urls_path, artifact_dir))
    with collection_lock(artifact_dir / "collection.lock"):
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        run_dir = artifact_dir / "runs" / run_id
        run_dir.mkdir(parents=True)
        file_log = logging.FileHandler(run_dir / "collection.log", encoding="utf-8")
        file_log.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.getLogger().addHandler(file_log)
        summary = {"run_id": run_id, "started_at_utc": datetime.now(timezone.utc).isoformat(),
                   "status": "failed", "output_path": str(output_path)}
        try:
            existing = pd.read_csv(output_path) if output_path.exists() else pd.DataFrame()
            if output_path.exists():
                validate_records(existing)
                # Latest pre-run copy; the working raw CSV remains the same file.
                shutil.copy2(output_path, artifact_dir / "jobs_before_latest_run.csv")
            old_urls = set(existing["url"]) if not existing.empty else set()
            summary["records_before"] = len(existing)

            collected, statistics = collect_job_urls(
                output_path=urls_path, delay=delay, headless=True,
            )
            if collected.empty:
                raise ValueError("No URLs collected; refusing to report success.")
            atomic_csv(collected, run_dir / "collected_urls.csv")
            atomic_csv(statistics, run_dir / "category_statistics.csv")
            current_urls = set(collected["url"])
            summary["collected_urls"] = len(current_urls)
            summary["new_candidates"] = len(current_urls - old_urls)
            if current_urls - old_urls:
                # Scrape into staging so failed validation cannot replace the main CSV.
                staging = run_dir / "jobs_staging.csv"
                if output_path.exists():
                    shutil.copy2(output_path, staging)
                results = scrape_jobs(
                    urls_path=urls_path, output_path=staging,
                    error_path=run_dir / "errors.csv", delay=delay,
                    headless=True, max_consecutive_page_errors=5,
                )
                validate_records(results)
                if not old_urls.issubset(set(results["url"])):
                    raise ValueError("Collection lost previously stored URLs.")
                atomic_csv(results, output_path)
                staging.unlink()
            else:
                results = existing
            missing = current_urls - set(results["url"])
            summary.update(records_after=len(results), new_records=len(results) - len(existing),
                           urls_without_record=len(missing),
                           status="partial" if missing else "complete")
            LOGGER.info("Collection summary: %s", summary)
            return 2 if missing else 0
        except Exception as error:
            summary["error"] = str(error)
            LOGGER.exception("Collection failed; inspect this run's logs and staging CSV.")
            return 1
        finally:
            summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
            (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            logging.getLogger().removeHandler(file_log)
            file_log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=3.0)
    args = parser.parse_args()
    if args.delay < 3:
        parser.error("Use at least 3 seconds between requests.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        return run_collection(delay=args.delay)
    except RuntimeError as error:
        LOGGER.error("%s", error)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
