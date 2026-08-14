from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

URLS_PATH = DATA_DIR / "nofluff_it_urls.csv"
OUTPUT_PATH = DATA_DIR / "nofluff_it_jobs.csv"
ERROR_PATH = DATA_DIR / "nofluff_scraping_errors.csv"

DEFAULT_DELAY = 1.0
CHECKPOINT_EVERY = 25

CATEGORIES = [
    "it",
    "backend",
    "frontend",
    "fullstack",
    "data",
    "ai",
    "devops",
    "security",
    "testing",
    "java",
    ".net",
    "python",
    "mobile",
    "cloud",
    "architecture",
    "business-analysis",
    "project-manager",
    "product-management",
    "support",
    "erp",
    "embedded",
    "qa",
    "ux-ui",
    "blockchain",
    "game",
]
