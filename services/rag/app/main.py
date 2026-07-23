"""DaD DeID Pipeline rag — 민감도별 분리 인덱싱 + 검색 (Epic 4).

POST /index      : 비식별된 청크 인덱싱 (민감도 namespace 분리)
POST /search     : 검색 (테넌트 격리 + 외부반출 게이트)
GET  /namespaces : namespace별 청크 수
GET  /health     : 헬스체크
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.index.schema import ChunkMetadata, SensitivityLevel
from app.index.store import IndexedChunk, InMemoryVectorStore, SearchHit

app = FastAPI(title="DaD DeID Pipeline rag", version="0.1.0")

VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "sqlite")  # sqlite | pgvector | qdrant | weaviate


def _make_store():
    """VECTOR_BACKEND 스위치. 연결/로드 실패 시 in-memory 폴백(개발 편의)."""
    if VECTOR_BACKEND == "pgvector":
        try:
            from app.index.pgvector_store import PgVectorStore
            dsn = os.getenv("DATABASE_URL", "postgresql://redactflow:devpass@localhost:5432/redactflow")
            return PgVectorStore(dsn.replace("postgres://", "postgresql://"))
        except Exception as e:  # noqa: BLE001
            print(f"[rag] pgvector 연결 실패 → in-memory 폴백: {e}")
    if VECTOR_BACKEND == "qdrant":
        try:
            from app.index.qdrant_store import QdrantStore
            return QdrantStore(os.getenv("QDRANT_URL") or None)
        except Exception as e:  # noqa: BLE001
            print(f"[rag] qdrant 초기화 실패 → in-memory 폴백: {e}")
    if VECTOR_BACKEND == "weaviate":
        try:
            from app.index.weaviate_store import WeaviateStore
            return WeaviateStore(os.getenv("WEAVIATE_URL") or None)
        except Exception as e:  # noqa: BLE001
            print(f"[rag] weaviate 초기화 실패 → in-memory 폴백: {e}")
    return InMemoryVectorStore()


_store = _make_store()
_metrics: dict[str, float] = {}                          # PRD §5 운영지표 (Epic 6)


def _inc(name: str, n: float = 1) -> None:
    _metrics[name] = _metrics.get(name, 0) + n


class IndexRequest(BaseModel):
    text: str
    metadata: ChunkMetadata


class SearchRequest(BaseModel):
    query: str
    project_id: str
    external: bool = Field(default=False, description="외부 LLM 반출 컨텍스트면 true → 민감 청크 차단")
    top_k: int = 5


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    export_blocked_count: int
    external: bool


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "rag", "vector_backend": VECTOR_BACKEND}


@app.post("/index")
def index(req: IndexRequest) -> dict:
    _store.upsert(IndexedChunk(metadata=req.metadata, text=req.text))
    _inc("chunks_indexed_total")
    return {
        "indexed": req.metadata.chunk_id,
        "namespace": req.metadata.sensitivity_level.value,
        "export_blocked": req.metadata.export_blocked(),
    }


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    hits, blocked = _store.query(req.query, req.project_id, req.external, req.top_k)
    _inc("searches_total")
    if req.external:
        _inc("llm_sensitive_block_total", blocked)    # PRD §5: 외부반출 차단 건수
    return SearchResponse(hits=hits, export_blocked_count=blocked, external=req.external)


@app.get("/namespaces")
def namespaces() -> dict:
    return {
        "namespaces": _store.namespaces(),
        "export_blocked_levels": [
            SensitivityLevel.RESTRICTED.value, SensitivityLevel.TRADE_SECRET.value
        ],
    }


@app.get("/metrics")
def metrics() -> dict:
    """PRD §5 운영지표 (llm_sensitive_block_total·chunks_indexed_total·searches_total)."""
    return dict(_metrics)
