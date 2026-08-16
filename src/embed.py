from __future__ import annotations

from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding


def _is_e5(name: str) -> bool:
    return "e5" in name.lower()


class LocalEmbedder:
    """CPU embeddings. Vault stays on the server; only retrieved snippets go to the LLM API."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)

    def embed_query(self, text: str) -> list[float]:
        payload = f"query: {text}" if _is_e5(self.model_name) else text
        vec = next(self.model.embed([payload[:4000]]))
        return np.asarray(vec, dtype=float).tolist()

    def embed_docs(self, texts: list[str]) -> list[list[float]]:
        payload = []
        for text in texts:
            chunk = text[:4000]
            payload.append(f"passage: {chunk}" if _is_e5(self.model_name) else chunk)
        return [np.asarray(vec, dtype=float).tolist() for vec in self.model.embed(payload)]


@lru_cache(maxsize=1)
def get_embedder(model_name: str) -> LocalEmbedder:
    return LocalEmbedder(model_name)
