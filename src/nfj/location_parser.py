import re
from urllib.parse import urlparse

from .utils import clean_text

CITY_SLUGS = {
    "warszawa": "Warszawa",
    "warsaw": "Warszawa",
    "krakow": "Kraków",
    "cracow": "Kraków",
    "gdansk": "Gdańsk",
    "gdynia": "Gdynia",
    "sopot": "Sopot",
    "wroclaw": "Wrocław",
    "poznan": "Poznań",
    "lodz": "Łódź",
    "katowice": "Katowice",
    "gliwice": "Gliwice",
    "bydgoszcz": "Bydgoszcz",
    "torun": "Toruń",
    "szczecin": "Szczecin",
    "lublin": "Lublin",
    "rzeszow": "Rzeszów",
    "bialystok": "Białystok",
    "olsztyn": "Olsztyn",
    "opole": "Opole",
    "kielce": "Kielce",
    "zielona-gora": "Zielona Góra",
    "gorzow-wielkopolski": "Gorzów Wielkopolski",
    "bielsko-biala": "Bielsko-Biała",
    "czestochowa": "Częstochowa",
    "radom": "Radom",
    "tychy": "Tychy",
}


def extract_job_locations(
    text,
    url=None,
):
    if text:
        patterns = [
            r"(?:^|\n)Lokalizacja:\s*([^\n]+)",
            r"(?:^|\n)Location:\s*([^\n]+)",
            r"(?:^|\n)Miejsce pracy:\s*([^\n]+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if match:
                value = clean_text(
                    match.group(1)
                )

                if value:
                    return value

    if url:
        try:
            slug = (
                urlparse(url)
                .path
                .rstrip("/")
                .split("/")[-1]
                .lower()
            )

            for city_slug, city_name in sorted(
                CITY_SLUGS.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            ):
                if re.search(
                    rf"(?:^|-){re.escape(city_slug)}(?:-|$)",
                    slug,
                ):
                    return city_name

        except Exception:
            pass

    return None
