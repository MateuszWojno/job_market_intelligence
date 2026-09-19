"""Backward-compatible exports for the parser modules.

Parser implementations are grouped by domain in dedicated modules. Existing
imports from ``nfj.parsers`` remain supported.
"""

from .company_parser import extract_company_info
from .experience_parser import parse_experience
from .job_details_parser import (
    extract_category,
    extract_contract_type,
    extract_offer_details,
    extract_start_date,
    extract_valid_until,
)
from .location_parser import CITY_SLUGS, extract_job_locations
from .salary_parser import (
    SALARY_PATTERN,
    SALARY_PERIOD_PATTERNS,
    extract_salary_period,
    parse_salary,
    parse_salary_options,
)
from .section_parser import (
    extract_nice_to_have,
    extract_offer_description,
    extract_required_skills,
    extract_requirements,
    extract_responsibilities,
)
from .workplace_parser import parse_workplace

__all__ = [
    "CITY_SLUGS",
    "SALARY_PATTERN",
    "SALARY_PERIOD_PATTERNS",
    "extract_category",
    "extract_company_info",
    "extract_contract_type",
    "extract_job_locations",
    "extract_nice_to_have",
    "extract_offer_description",
    "extract_offer_details",
    "extract_required_skills",
    "extract_requirements",
    "extract_responsibilities",
    "extract_salary_period",
    "extract_start_date",
    "extract_valid_until",
    "parse_experience",
    "parse_salary",
    "parse_salary_options",
    "parse_workplace",
]
