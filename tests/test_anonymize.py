"""PII anonymization tests (AG-3, P4)."""

from its.llm.anonymize import scrub


def test_name_scrubbed() -> None:
    assert "[NAME]" in scrub("Sven Weidenmann hat Mühe mit Brüchen.")


def test_date_scrubbed() -> None:
    assert "[DATE]" in scrub("geboren am 12.03.2011")


def test_email_scrubbed() -> None:
    assert "[EMAIL]" in scrub("Kontakt: a.b-c@school-zh.ch bitte.")


def test_anonymized_agent_context_unchanged() -> None:
    # The agent only ever sends skill keys + intents — these must pass through intact.
    s = "Skill: complete-the-square. Modus: explain. Hinweis erwuenscht."
    assert scrub(s) == s
