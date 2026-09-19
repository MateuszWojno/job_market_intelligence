import re

def parse_workplace(text):
    if not text:
        return None

    if re.search(
        r"Hybryd|"
        r"Praca zdalna przez\s+\d+\s+dni?|"
        r"Praca zdalna:\s*Elastyczna|"
        r"\bHybrid\b",
        text,
        re.IGNORECASE,
    ):
        return "Hybrid"

    if re.search(
        r"Praca w pełni zdalna|"
        r"100%\s*(?:praca\s*)?zdalna|"
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

