import re

def parse_workplace(text):
    if not text:
        return None

    if re.search(r"(?im)^\s*(?:Bez pracy zdalnej|No remote work)\s*[.!]?\s*$", text):
        return "Onsite"

    if re.search(
        r"Hybryd|"
        r"Praca zdalna przez\s+[1-4]\s+(?:dzień|dni)\b|"
        r"Liczba dni zdalnych do ustalenia|"
        r"Praca zdalna:\s*Elastyczna|"
        r"\bHybrid\b",
        text,
        re.IGNORECASE,
    ):
        return "Hybrid"

    if re.search(
        r"Praca w pełni zdalna|"
        r"100\s*%\s*(?:(?:współ)?praca\s*)?zdalna|"
        r"\bFully remote\b|"
        r"\bRemote\b",
        text,
        re.IGNORECASE,
    ):
        return "Remote"

    if re.search(
        r"\bOnsite\b|"
        r"\bOn-site\b|"
        r"\bStacjonarn",
        text,
        re.IGNORECASE,
    ):
        return "Onsite"

    return None


# ============================================================
# COMPANY INFO

