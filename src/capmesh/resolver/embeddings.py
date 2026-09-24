"""Local embedding engine using sentence-transformers."""
from __future__ import annotations

import math

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False


class EmbeddingEngine:
    """Compute embeddings for semantic similarity search.

    Uses sentence-transformers with all-MiniLM-L6-v2 (22M params, ~80MB).
    Falls back gracefully if not installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = None
        if _ST_AVAILABLE:
            self._model = SentenceTransformer(model_name)

    @property
    def available(self) -> bool:
        return self._model is not None

    def embed(self, text: str) -> list[float] | None:
        if not self.available:
            return None
        vec = self._model.encode(text, convert_to_numpy=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]] | None:
        if not self.available:
            return None
        vecs = self._model.encode(texts, convert_to_numpy=True)
        return [v.tolist() for v in vecs]

    def similarity(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
