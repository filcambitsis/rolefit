import hashlib
import html
import re

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 42
FAMILIES = ["AI Engineer", "ML Engineer", "Data Scientist", "Data Analyst", "AI/Technology Consultant"]


def strip_html(value: str) -> str:
    soup = BeautifulSoup(html.unescape(value), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


def content_hash(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()


def family(title: str) -> str | None:
    value = title.lower()
    if re.search(r"consult", value) and re.search(r"\b(ai|data|technology|digital|analytics)\b", value):
        return FAMILIES[4]
    if re.search(r"data scien|research scien|applied scien", value):
        return FAMILIES[2]
    if re.search(
        r"data analyst|analytics engineer|business intelligence|product analyst|analytics analyst", value
    ):
        return FAMILIES[3]
    if re.search(r"machine learning|\bml\b|mlops", value):
        return FAMILIES[1]
    if re.search(r"\bai\b|artificial intelligence|\bllm\b|generative|deep learning", value) and re.search(
        r"engineer|developer", value
    ):
        return FAMILIES[0]
    return None


def employment(value: str, text: str) -> tuple[str, str]:
    def match(s):
        s = re.sub(r"[^a-z]", "", s.lower())
        if "intern" in s:
            return "internship"
        if "parttime" in s:
            return "part-time"
        if "fulltime" in s:
            return "full-time"
        if "contract" in s or "temporary" in s:
            return "other"
        return None

    if value:
        return match(value) or "unknown", "structured"
    # Do not assume every permanent posting is full time.
    found = re.search(r"\b(intern(?:ship)?|part[ -]time|full[ -]time|contract|temporary)\b", text, re.I)
    return (match(found[0]) or "unknown", "inferred") if found else ("unknown", "unknown")


def workplace(value: str, location: str, text: str) -> tuple[str, str]:
    for label in ["hybrid", "remote", "onsite", "on-site"]:
        if label in value.lower():
            return ("on-site" if label == "onsite" else label), "structured"
    for label in ["hybrid", "remote", "on-site", "onsite"]:
        if re.search(r"\b" + label + r"\b", location.lower()):
            return ("on-site" if label == "onsite" else label), "inferred"
    return "unknown", "unknown"


COUNTRIES = {
    "NL": ["netherlands", "amsterdam", "rotterdam", "utrecht", "eindhoven"],
    "GB": ["united kingdom", "london", "cambridge", "manchester", "edinburgh"],
    "DE": ["germany", "berlin", "munich", "hamburg", "münchen"],
    "FR": ["france", "paris"],
    "IE": ["ireland", "dublin"],
    "US": [
        "united states",
        "new york",
        "san francisco",
        "seattle",
        "boston",
        "palo alto",
        "austin",
        "mountain view",
        "sunnyvale",
        "san jose",
    ],
    "CA": ["canada", "toronto", "vancouver", "montreal"],
    "ES": ["spain", "madrid", "barcelona"],
    "CH": ["switzerland", "zurich", "zürich"],
    "PL": ["poland", "warsaw", "krakow"],
    "IN": ["india", "bengaluru", "bangalore", "hyderabad"],
    "SG": ["singapore"],
    "AU": ["australia", "sydney", "melbourne"],
}


def countries(location: str, explicit: str = "") -> list[str]:
    values = []
    for code, aliases in COUNTRIES.items():
        if explicit.upper() == code or any(
            re.search(r"\b" + re.escape(a) + r"\b", f"{location} {explicit}", re.I) for a in aliases
        ):
            values.append(code)
    return values


def language(text: str) -> str:
    try:
        return detect(text[:12000]) if len(text) > 60 else "unknown"
    except LangDetectException:
        return "unknown"


def minimum_years(text: str) -> float | None:
    match = re.search(r"\b(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\s*\+?\s*years?\b", text, re.I)
    return float(match[1]) if match else None
