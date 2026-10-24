import re

from selenium.webdriver.common.by import By


def clean_text(text):
    if text is None:
        return None

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_body_text(driver):
    try:
        element = driver.find_element(
            By.TAG_NAME,
            "body"
        )

        text = element.text

    except Exception:
        return ""

    if not text:
        return ""

    return (
        text
        .replace("\xa0", " ")
        .strip()
    )


def get_main_offer_text(body_text):
    if not body_text:
        return ""

    markers = [
        r"ZOBACZ PODOBNE OFERTY",
        r"PODOBNE OFERTY",
        r"SIMILAR JOBS",
    ]

    result = body_text

    for marker in markers:
        result = re.split(
            marker,
            result,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

    return result.strip()


def get_text(
    driver,
    selectors
):
    for selector in selectors:
        try:
            elements = driver.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:
                text = clean_text(
                    element.text
                )

                if text:
                    return text

        except Exception:
            continue

    return None


def get_all_text(
    driver,
    selectors
):
    values = []

    for selector in selectors:
        try:
            elements = driver.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:
                text = clean_text(
                    element.text
                )

                if text:
                    values.append(
                        text
                    )

        except Exception:
            continue

    return values


def get_job_id(url):
    if not url:
        return None

    try:
        return (
            url
            .rstrip("/")
            .split("/job/")[-1]
        )

    except Exception:
        return None
