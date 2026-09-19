"""Backward-compatible imports for the scraper's public API.

New code should import from ``job_scraper``, ``pipeline`` or ``refresh``.
"""

from .job_scraper import (
    INVALID_PAGE_MARKERS,
    InvalidJobPageError,
    scrape_job,
    scrape_one_job,
    validate_job_page,
)
from .pipeline import scrape_jobs
from .refresh import refresh_job_records, refresh_missing_salary_periods

__all__ = [
    "INVALID_PAGE_MARKERS",
    "InvalidJobPageError",
    "refresh_job_records",
    "refresh_missing_salary_periods",
    "scrape_job",
    "scrape_jobs",
    "scrape_one_job",
    "validate_job_page",
]
