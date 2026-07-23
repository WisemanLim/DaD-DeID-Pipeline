"""Qdrant VectorStore 어댑터 (Epic 4 / VECTOR_BACKEND=qdrant).

qdrant-client. QDRANT_URL 설정 시 원격, 아니면 로컬 in-memory(:memory:) — 오프라인 테스트 가능.
임베딩 = embedder(실 모델 또는 해시). namespace=민감도 payload, project_id 테넌트 격리,
RESTRICTED/TRADE_SECRET 외부반출 게이트는 query filter 로.
"""
from __future__ import annotations

import hashlib

from app.index.embedder import get_embedder
from app.index.schema import SensitivityLevel
from app.index.store import IndexedChunk, SearchHit, VectorStore

_COLLECTION = "rag_chunks"
_BLOCKED = (SensitivityLevel.RESTRICTED.value, SensitivityLevel.TRADE_SECRET.value)


def _point_id(chunk_id: str) -> int:
    return int(hashlib.sha256(chunk_id.encode()).hexdigest()[:15], 16)


class QdrantStore(VectorStore):
    def __init__(self, url: str | None = None) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._emb = get_embedder()
        self._client = QdrantClient(url=url) if url else QdrantClient(location=":memory:")
        if not self._client.collection_exists(_COLLECTION):
            self._client.create_collection(
                _COLLECTION,
                vectors_config=VectorParams(size=self._emb.dim, distance=Distance.COSINE),
            )

    def upsert(self, chunk: IndexedChunk) -> None:
        from qdrant_client.models import PointStruct

        m = chunk.metadata
        self._client.upsert(_COLLECTION, points=[PointStruct(
            id=_point_id(m.chunk_id),
            vector=self._emb.embed(chunk.text),
            payload={
                "chunk_id": m.chunk_id, "document_id": m.document_id,
                "project_id": m.project_id, "sensitivity": m.sensitivity_level.value,
                "text": chunk.text,
            },
        )])

    def query(self, text, project_id, external, top_k=5):
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

        must = [FieldCondition(key="project_id", match=MatchValue(value=project_id))]
        must_not = []
        blocked = 0
        if external:
            blocked = self._client.count(_COLLECTION, count_filter=Filter(must=[
                FieldCondition(key="project_id", match=MatchValue(value=project_id)),
                FieldCondition(key="sensitivity", match=MatchAny(any=list(_BLOCKED))),
            ])).count
            must_not.append(FieldCondition(key="sensitivity", match=MatchAny(any=list(_BLOCKED))))
        res = self._client.query_points(
            _COLLECTION, query=self._emb.embed(text),
            query_filter=Filter(must=must, must_not=must_not), limit=top_k,
        ).points
        hits = [SearchHit(
            chunk_id=p.payload["chunk_id"], document_id=p.payload["document_id"],
            sensitivity_level=SensitivityLevel(p.payload["sensitivity"]),
            score=round(float(p.score), 4), text=p.payload["text"],
        ) for p in res]
        return hits, blocked

    def namespaces(self) -> dict[str, int]:
        out: dict[str, int] = {}
        offset = None
        while True:
            points, offset = self._client.scroll(_COLLECTION, limit=256, offset=offset, with_payload=True)
            for p in points:
                s = p.payload["sensitivity"]
                out[s] = out.get(s, 0) + 1
            if offset is None:
                break
        return dict(sorted(out.items()))
