"""Unit tests for the markdown parser (CON-1) — no DB, fast."""

from its.content.parser import parse_note

MD = """---
skill: complete-the-square
subject: math
---

# Titel

Erklaerender Prosatext ueber das Thema. Verwandt: [[quadratic-formula]].

```sql
SELECT avg(mastery) FROM learner_state;
```

Noch ein Absatz nach dem Codeblock.
"""


def test_frontmatter_parsed() -> None:
    p = parse_note(MD)
    assert p.frontmatter["skill"] == "complete-the-square"
    assert p.frontmatter["subject"] == "math"


def test_code_fence_split_from_prose() -> None:
    p = parse_note(MD)
    assert "SELECT avg(mastery)" not in p.prose  # NOT embedded
    assert p.sidecar_queries == ["SELECT avg(mastery) FROM learner_state;"]


def test_wikilinks_extracted() -> None:
    p = parse_note(MD)
    assert p.links == ["quadratic-formula"]


def test_prose_excludes_frontmatter_and_keeps_text() -> None:
    p = parse_note(MD)
    assert "skill:" not in p.prose
    assert "Erklaerender Prosatext" in p.prose
    assert "Noch ein Absatz" in p.prose


def test_note_without_frontmatter() -> None:
    p = parse_note("Nur Prosa, kein Frontmatter.")
    assert p.frontmatter == {}
    assert p.prose == "Nur Prosa, kein Frontmatter."
    assert p.sidecar_queries == []
