"""VectorStore 추상화 (Epic 4) — 민감도별 namespace 분리 + 테넌트 격리 + 외부반출 게이트.

PRD §3 ⓔ: industry_code·sensitivity_level·transform_action·lineage 부여, 민감도별 namespace 분리,
RESTRICTED/TRADE_SECRET 외부 LLM 반출 차단.
임베딩은 오프라인 결정적 placeholder(토큰 Jaccard) — PRD: 검색 정확도 튜닝은 Out of scope.
백엔드 env 스위치(VECTOR_BACKEND): 기본 in-memory, dev+ pgvector/qdrant 어댑터로 교체.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.index.schema import ChunkMetadata, SensitivityLevel

_TOKEN = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN.findall(text)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class IndexedChunk(BaseModel):
    metadata: ChunkMetadata
    text: str


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    sensitivity_level: SensitivityLevel
    score: float
    text: str


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, chunk: IndexedChunk) -> None: ...

    @abstractmethod
    def query(
        self, text: str, project_id: str, external: bool, top_k: int = 5
    ) -> tuple[list[SearchHit], int]: ...

    @abstractmethod
    def namespaces(self) -> dict[str, int]: ...


class InMemoryVectorStore(VectorStore):
    """namespace = sensitivity_level. 테넌트는 project_id 로 격리(크로스테넌트 누출 0)."""

    def __init__(self) -> None:
        # {sensitivity_level: [IndexedChunk]}
        self._ns: dict[str, list[IndexedChunk]] = {}

    def upsert(self, chunk: IndexedChunk) -> None:
        ns = chunk.metadata.sensitivity_level.value
        bucket = self._ns.setdefault(ns, [])
        # 동일 chunk_id 는 교체(idempotent upsert)
        bucket[:] = [c for c in bucket if c.metadata.chunk_id != chunk.metadata.chunk_id]
        bucket.append(chunk)

    def query(
        self, text: str, project_id: str, external: bool, top_k: int = 5
    ) -> tuple[list[SearchHit], int]:
        q = _tokens(text)
        hits: list[SearchHit] = []
        blocked = 0
        for chunks in self._ns.values():
            for c in chunks:
                # 테넌트 격리 — 다른 project 는 후보에서 제외(RLS 등가)
                if c.metadata.project_id != project_id:
                    continue
                # 외부 반출 게이트 — RESTRICTED/TRADE_SECRET 차단
                if external and c.metadata.export_blocked():
                    blocked += 1
                    continue
                score = _jaccard(q, _tokens(c.text))
                if score > 0:
                    hits.append(SearchHit(
                        chunk_id=c.metadata.chunk_id, document_id=c.metadata.document_id,
                        sensitivity_level=c.metadata.sensitivity_level,
                        score=round(score, 4), text=c.text,
                    ))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k], blocked

    def namespaces(self) -> dict[str, int]:
        return {ns: len(chunks) for ns, chunks in sorted(self._ns.items())}
