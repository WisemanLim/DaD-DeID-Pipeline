"""Qdrant 어댑터 + 임베딩 시험 (impl/11) — 로컬 in-memory 모드(오프라인)."""
from app.index.embedder import HashEmbedder, get_embedder
from app.index.qdrant_store import QdrantStore
from app.index.schema import ChunkMetadata
from app.index.store import IndexedChunk


def _meta(cid, lvl, proj="qproj"):
    return ChunkMetadata(
        document_id="d", chunk_id=cid, industry_code="Q", sensitivity_level=lvl,
        transform_action="MASK", lineage={}, source_uri="s", domain="healthcare-clinical",
        project_id=proj, owner="u", version="1",
    )


def test_embedder_loads():
    emb = get_embedder()
    v = emb.embed("환자 차트 혈압")
    assert len(v) == emb.dim
    assert emb.dim > 0


def test_hash_embedder_deterministic():
    h = HashEmbedder()
    assert h.embed("같은 입력") == h.embed("같은 입력")
    assert h.dim == 64


def test_qdrant_namespace_separation():
    s = QdrantStore()                       # :memory:
    s.upsert(IndexedChunk(metadata=_meta("q1", "PUBLIC"), text="공개 혈압 안내"))
    s.upsert(IndexedChunk(metadata=_meta("q2", "RESTRICTED"), text="환자 차트 혈압"))
    ns = s.namespaces()
    assert ns.get("PUBLIC") == 1 and ns.get("RESTRICTED") == 1


def test_qdrant_external_gate():
    """외부반출 게이트 — RESTRICTED/TRADE_SECRET 차단."""
    s = QdrantStore()
    s.upsert(IndexedChunk(metadata=_meta("q1", "PUBLIC"), text="공개 혈압 안내"))
    s.upsert(IndexedChunk(metadata=_meta("q2", "RESTRICTED"), text="환자 차트 혈압 기록"))
    hits, blocked = s.query("혈압", "qproj", external=True)
    assert blocked >= 1
    assert all(h.sensitivity_level.value == "PUBLIC" for h in hits)


def test_qdrant_tenant_isolation():
    s = QdrantStore()
    s.upsert(IndexedChunk(metadata=_meta("a1", "INTERNAL", "projA"), text="기밀 혈압"))
    s.upsert(IndexedChunk(metadata=_meta("b1", "INTERNAL", "projB"), text="기밀 혈압"))
    hits, _ = s.query("기밀 혈압", "projA", external=False)
    assert all(h.chunk_id == "a1" for h in hits)
    assert len(hits) == 1
