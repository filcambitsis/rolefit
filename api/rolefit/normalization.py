import hashlib
import html
import re

from bs4 import BeautifulSoup
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 42
FAMILIES = [
    "AI Engineer",
    "ML Engineer",
    "Data Scientist",
    "Data Analyst",
    "Data Engineer",
    "Software Engineer",
    "AI Consulting & Solutions",
    "Data Consultant",
    "Technology Consultant",
    "AI & Automation Specialist",
    "Solutions Engineer",
    "Product Analyst",
    "Business & Technology Analyst",
]


FAMILY_ALIASES = {
    "AI Consultant": "AI Consulting & Solutions",
    "AI Solutions & Implementation": "AI Consulting & Solutions",
}


def strip_html(value: str) -> str:
    soup = BeautifulSoup(html.unescape(value), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


def content_hash(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()


def family(title: str) -> str | None:
    """Role family from the job title, or None if the job is out of scope."""
    value = title.lower()
    ai = bool(
        re.search(r"\bai\b|artificial intelligence|machine learning|gen\s?ai|generative|\bllm\b", value)
    )
    if re.search(r"\bproduct owner\b", value):
        return None
    if ai and re.search(r"solutions?|implementation|adoption", value):
        return "AI Consulting & Solutions"
    if re.search(r"\bproduct analyst\b", value):
        return "Product Analyst"
    if re.search(r"\b(?:business|technology|solutions?) analyst\b", value):
        return "Business & Technology Analyst"
    if re.search(r"\b(?:consultant|consulting|advisor)\b", value):
        if ai:
            return "AI Consulting & Solutions"
        if re.search(r"\bdata\b|analytics|business intelligence", value):
            return "Data Consultant"
        if re.search(r"technology|technical|digital|innovation|\bit\b|solutions?", value):
            return "Technology Consultant"
    if ai and re.search(r"adoption|transformation|implementation", value):
        return "AI Consulting & Solutions"
    if re.search(r"\bsolutions? (?:engineer|architect)\b", value):
        return "Solutions Engineer"
    # Industrial and QA automation are outside this app's software/data scope.
    if re.search(r"automation", value) and re.search(r"industrial|plc|controls?|test|qa", value):
        return None
    if re.search(r"automation|\brpa\b", value) and re.search(
        r"engineer|developer|specialist|workflow", value
    ):
        return "AI & Automation Specialist"
    if ai and re.search(r"specialist", value) and not re.search(r"support|sales|recruit", value):
        return "AI & Automation Specialist"
    if re.search(r"data scien|research scien|applied scien", value):
        return "Data Scientist"
    if re.search(r"data analyst|analytics engineer|business intelligence|analytics analyst", value):
        return "Data Analyst"
    if re.search(r"machine learning|\bml\b|mlops", value):
        return "ML Engineer"
    if (ai or "deep learning" in value) and re.search(r"engineer|developer", value):
        return "AI Engineer"
    if re.search(r"\bdata (?:platform |warehouse )?engineer", value):
        return "Data Engineer"
    if re.search(
        r"\b(?:software|back[ -]?end|front[ -]?end|full[ -]?stack|mobile|ios|android|web) (?:engineer|developer)",
        value,
    ):
        return "Software Engineer"
    return None


def career_level(title: str, employment_type: str = "") -> str:
    """Only classify explicit title signals; an unmarked title is not automatically mid-level."""
    value = title.lower()
    if employment_type == "internship" or re.search(r"\bintern(?:ship)?\b", value):
        return "internship"
    if re.search(r"\b(?:lead|staff|principal|manager|head|director)\b", value):
        return "lead"
    if re.search(r"\b(?:senior|sr)\b", value):
        return "senior"
    if re.search(r"\b(?:junior|jr|graduate|entry[ -]level)\b", value):
        return "junior"
    if re.search(r"\b(?:mid[ -]level|medior|intermediate)\b", value):
        return "mid"
    return "unknown"


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
    "GR": ["greece", "ελλάδα", "athens", "αθήνα", "thessaloniki", "θεσσαλονίκη"],
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
    # Structured country codes take precedence over ambiguous city names.
    if explicit.strip().upper() in COUNTRIES:
        return [explicit.strip().upper()]
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
