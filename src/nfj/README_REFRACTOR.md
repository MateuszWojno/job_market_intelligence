# NFJ scraper - struktura po refaktoryzacji

W folderze `src` utwórz folder:

```text
src/
└── nfj/
    ├── __init__.py
    ├── config.py
    ├── driver.py
    ├── parsers.py
    ├── scraper.py
    ├── storage.py
    ├── urls.py
    └── utils.py
```

Stary plik `src/nofluffjobs_api.py` możesz na początku zostawić jako kopię zapasową.
Po sprawdzeniu nowej wersji możesz go usunąć.

## Notebook

Jeżeli notebook znajduje się w:

`G:\pandas\job_market_intelligence\notebooks`

użyj:

```python
from pathlib import Path
import sys

PROJECT_ROOT = Path.cwd().parent
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from nfj import (
    collect_job_urls,
    scrape_jobs,
    scrape_one_job,
)
```

Test importu:

```python
import nfj

print(hasattr(nfj, "collect_job_urls"))
print(hasattr(nfj, "scrape_jobs"))
```

Oczekiwany wynik:

```text
True
True
```

## Zbieranie URL-i

```python
df_urls, df_stats = collect_job_urls(
    categories=["data"],
    max_pages_per_category=2,
)

df_stats
```

Po teście możesz pobrać wszystkie kategorie:

```python
df_urls, df_stats = collect_job_urls()
```

## Test szczegółów ofert

```python
df_test = scrape_jobs(max_jobs=5)
df_test
```

## Pełny scraping

```python
df_jobs = scrape_jobs()
```
