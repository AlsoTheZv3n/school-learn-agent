"""Embedding interface + a deterministic, dependency-free stub.

The real embedding model is still an open decision (see
docs/planning/open-questions-and-risks.md, E2/E4) and is wired together with the
LLM client in AG-3. Until then `HashingEmbedder` lets the ingestion + semantic
retrieval pipeline run end-to-end and be tested deterministically.

It is a signed hashing vectorizer (a "feature hashing" embedder): each token is
hashed into one of EMBEDDING_DIM buckets with a sign, then the vector is L2-
normalized. It is NOT a semantic model, but lexical overlap yields higher cosine
similarity — enough to demonstrate and test the retrieval path. Keep dim ==
EMBEDDING_DIM so the swap to a real model needs no schema change at the same dim.
"""

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

from its.db.models import EMBEDDING_DIM

_TOKEN = re.compile(r"\w+", re.UNICODE)


@runtime_checkable
class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    """Deterministic stub embedder (signed feature hashing). See module docstring."""

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            h = int.from_bytes(digest, "big")
            idx = h % self.dim
            sign = 1.0 if (h >> 63) & 1 else -1.0  # signed hashing reduces collisions
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            vec[0] = 1.0  # avoid a zero vector (cosine distance is undefined)
            return vec
        return [v / norm for v in vec]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


_default: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the configured embedder.

    TODO (AG-3): switch on settings.llm_backend to a real local/frontier embedding
    model. For now always the deterministic stub.
    """
    global _default
    if _default is None:
        _default = HashingEmbedder()
    return _default
