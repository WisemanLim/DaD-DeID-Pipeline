"""deid 임베딩 — classifier ML 판정용. 실 모델 우선, 해시 폴백 (rag embedder 와 동일 전략)."""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache

_DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class HashEmbedder:
    dim = 64
    name = "hash"

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in text.lower().split():
            h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm for v in vec] if norm else vec


class STEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._m = SentenceTransformer(model_name)
        get_dim = getattr(self._m, "get_embedding_dimension", None) or \
            self._m.get_sentence_embedding_dimension
        self.dim = get_dim()
        self.name = model_name

    def embed(self, text: str) -> list[float]:
        return self._m.encode(text, normalize_embeddings=True).tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._m.encode(texts, normalize_embeddings=True)]


@lru_cache(maxsize=1)
def get_embedder():
    if os.getenv("EMBED_BACKEND", "auto") == "hash":
        return HashEmbedder()
    try:
        return STEmbedder(os.getenv("EMBED_MODEL", _DEFAULT_MODEL))
    except Exception as e:  # noqa: BLE001
        print(f"[deid] 실 임베딩 미가용 → 해시 폴백: {e}")
        return HashEmbedder()


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))
