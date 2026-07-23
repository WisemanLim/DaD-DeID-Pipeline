"""임베딩 추상화 — 실 모델(sentence-transformers) 우선, 미가용 시 해시 폴백.

EMBED_MODEL(env, 기본 다국어 MiniLM). 모델 로드 실패(미설치/오프라인)면 HashEmbedder 로 graceful.
VectorStore(qdrant/pgvector) + classifier judge 가 공통 사용.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache

_DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_HASH_DIM = 64


class HashEmbedder:
    """결정적 해시 임베딩 (오프라인 폴백, 검색튜닝 Out-of-scope)."""

    dim = _HASH_DIM
    name = "hash"

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in text.lower().split():
            h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm for v in vec] if norm else vec


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        get_dim = getattr(self._model, "get_embedding_dimension", None) or \
            self._model.get_sentence_embedding_dimension
        self.dim = get_dim()
        self.name = model_name

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()


@lru_cache(maxsize=1)
def get_embedder():
    """실 모델 우선, 실패 시 해시 폴백. 1회 캐시."""
    if os.getenv("EMBED_BACKEND", "auto") == "hash":
        return HashEmbedder()
    try:
        return SentenceTransformerEmbedder(os.getenv("EMBED_MODEL", _DEFAULT_MODEL))
    except Exception as e:  # noqa: BLE001
        print(f"[rag] 실 임베딩 모델 미가용 → 해시 폴백: {e}")
        return HashEmbedder()
