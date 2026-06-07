"""Markdown parser (CON-1): split prose from code fences, extract wikilinks.

Core rule: the code block is NOT embedded with the prose — SQL/Cypher tokens skew
the vector. Prose is embedded; the query is kept as sidecar metadata. A small
frontmatter block (--- key: value ---) is parsed for routing (e.g. `skill:`).
"""

import re
from dataclasses import dataclass, field

FENCE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_SIDECAR_LANGS = {"sql", "cypher"}


@dataclass
class ParsedNote:
    prose: str  # markdown WITHOUT code fences or frontmatter
    sidecar_queries: list[str]  # extracted ```sql / ```cypher blocks
    links: list[str]  # targets from [[wikilinks]]
    frontmatter: dict[str, str] = field(default_factory=dict)


def _split_frontmatter(md: str) -> tuple[dict[str, str], str]:
    m = _FRONTMATTER.match(md)
    if not m:
        return {}, md
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm, md[m.end():]


def parse_note(md: str) -> ParsedNote:
    frontmatter, body = _split_frontmatter(md)
    queries = [
        block.strip()
        for lang, block in FENCE.findall(body)
        if (lang or "").lower() in _SIDECAR_LANGS
    ]
    prose = FENCE.sub("", body).strip()  # remove code fences -> clean embedding input
    links = WIKILINK.findall(prose)
    return ParsedNote(prose=prose, sidecar_queries=queries, links=links, frontmatter=frontmatter)
