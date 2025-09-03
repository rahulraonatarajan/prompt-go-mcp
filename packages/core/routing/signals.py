import re

FRESH_WORDS = r"(today|latest|price|pricing|schedule|release|news|update|who\s+is|20\d{2}|policy|changelog|version|deprecat|breaking)"
COMPLEX_VERBS = r"(implement|scaffold|integrate|deploy|refactor|migrate|benchmark|write tests|generate project|create pr|scrape|automate|pipeline|dataset)"
AMBIGUOUS = r"\b(best|cheapest|fastest|quickest|near me|for my use case|recommend)\b"


def has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.IGNORECASE) is not None

