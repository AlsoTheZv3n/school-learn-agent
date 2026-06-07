"""PII anonymization (AG-3, safety-critical). Applied before ANY external LLM call.

It is about minors (P4). Defense in depth: the agent is already given only IDs and
skill keys (never "Sven, 14, struggles with …"); scrub is the second line that
removes names, dates and emails should any slip into a prompt.
"""

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[A-ZÄÖÜ][a-zäöü]+\s[A-ZÄÖÜ][a-zäöü]+\b"), "[NAME]"),
    (re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b"), "[DATE]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
]


def scrub(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text
