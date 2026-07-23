"""Weaviate VectorStore 어댑터 (Epic 4 / VECTOR_BACKEND=weaviate).

weaviate-client v4. WEAVIATE_URL(또는 host/port) 연결. 임베딩 = 공통 embedder(BYO 벡터).
namespace=민감도 property, project_id 테넌트 격리, RESTRICTED/TRADE_SECRET 외부반출 게이트는 filter 로.
서버 미가용 시 connect 에서 예외 → 호출부가 in-memory 폴백.
"""
from __future__ import annotations

import hashlib
import os

from app.index.embedder import get_embedder
from app.index.schema import SensitivityLevel
from app.index.store import IndexedChunk, SearchHit, VectorStore

_CLASS = "RagChunk"
_BLOCKED = (SensitivityLevel.RESTRICTED.value, SensitivityLevel.TRADE_SECRET.value)


def _uuid(chunk_id: str) -> str:
    h = hashlib.sha256(chunk_id.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


class WeaviateStore(VectorStore):
    def __init__(self, url: str | None = None) -> None:
        import weaviate

        self._emb = get_embedder()
        url = url or os.getenv("WEAVIATE_URL", "http://localhost:8080")
        self._client = weaviate.connect_to_custom(
            http_host=url.split("://")[-1].split(":")[0],
            http_port=int(url.rsplit(":", 1)[-1]) if ":" in url.split("://")[-1] else 8080,
            http_secure=url.startswith("https"),
            grpc_host=url.split("://")[-1].split(":")[0],
            grpc_port=50051, grpc_secure=False, skip_init_checks=True,
        )
        if not self._client.collections.exists(_CLASS):
            import weaviate.classes.config as wvc

            self._client.collections.create(
                _CLASS,
                properties=[
                    wvc.Property(name="chunk_id", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="document_id", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="project_id", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="sensitivity", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="text", data_type=wvc.DataType.TEXT),
                ],
                vectorizer_config=wvc.Configure.Vectorizer.none(),
            )
        self._col = self._client.collections.get(_CLASS)

    def upsert(self, chunk: IndexedChunk) -> None:
        m = chunk.metadata
        self._col.data.insert(
            uuid=_uuid(m.chunk_id),
            properties={
                "chunk_id": m.chunk_id, "document_id": m.document_id,
                "project_id": m.project_id, "sensitivity": m.sensitivity_level.value,
                "text": chunk.text,
            },
            vector=self._emb.embed(chunk.text),
        )

    def query(self, text, project_id, external, top_k=5):
        import weaviate.classes.query as wq

        flt = wq.Filter.by_property("project_id").equal(project_id)
        blocked = 0
        if external:
            blocked = self._count(project_id, blocked_only=True)
            for lvl in _BLOCKED:
                flt = flt & wq.Filter.by_property("sensitivity").not_equal(lvl)
        res = self._col.query.near_vector(
            near_vector=self._emb.embed(text), limit=top_k, filters=flt,
            return_metadata=wq.MetadataQuery(distance=True),
        )
        hits = [SearchHit(
            chunk_id=o.properties["chunk_id"], document_id=o.properties["document_id"],
            sensitivity_level=SensitivityLevel(o.properties["sensitivity"]),
            score=round(1 - (o.metadata.distance or 0), 4), text=o.properties["text"],
        ) for o in res.objects]
        return hits, blocked

    def _count(self, project_id, blocked_only=False) -> int:
        import weaviate.classes.query as wq

        flt = wq.Filter.by_property("project_id").equal(project_id)
        if blocked_only:
            sub = None
            for lvl in _BLOCKED:
                cond = wq.Filter.by_property("sensitivity").equal(lvl)
                sub = cond if sub is None else (sub | cond)
            flt = flt & sub
        return self._col.aggregate.over_all(filters=flt).total_count

    def namespaces(self) -> dict[str, int]:
        import weaviate.classes.query as wq

        out: dict[str, int] = {}
        for lvl in SensitivityLevel:
            n = self._col.aggregate.over_all(
                filters=wq.Filter.by_property("sensitivity").equal(lvl.value)
            ).total_count
            if n:
                out[lvl.value] = n
        return dict(sorted(out.items()))
