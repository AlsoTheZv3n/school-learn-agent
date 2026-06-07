"""Curated content vault ingestion (Obsidian-style markdown).

Core rule (prevents bad retrieval): code fences (```sql / ```cypher) are NOT
embedded — they are kept as sidecar metadata. Only prose is embedded. Wikilinks
([[target]]) become typed edges in the skill graph.
"""
