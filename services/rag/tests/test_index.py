"""rag 분리 인덱싱 시험 — namespace 분리 / 외부반출 게이트 / 테넌트 격리."""
from fastapi.testclient import TestClient

from app.main import app, _store
from app.index.schema import SensitivityLevel
from app.index.store import InMemoryVectorStore

client = TestClient(app)


def _meta(chunk_id, level, project="proj-A", doc="doc1"):
    return {
        "document_id": doc, "chunk_id": chunk_id, "industry_code": "Q",
        "sensitivity_level": level, "transform_action": "MASK",
        "lineage": {"rule_id": "X", "policy_id": "p1"},
        "source_uri": "s3://x", "domain": "healthcare-clinical",
        "project_id": project, "owner": "u1", "version": "1",
    }


def setup_function():
    # 각 테스트 격리 — 전역 store 초기화
    _store.__init__()


def test_index_separates_namespaces():
    client.post("/index", json={"text": "혈압 측정 결과", "metadata": _meta("c1", "PUBLIC")})
    client.post("/index", json={"text": "환자 차트 기록", "metadata": _meta("c2", "RESTRICTED")})
    client.post("/index", json={"text": "촉매 배합 공정", "metadata": _meta("c3", "TRADE_SECRET")})
    ns = client.get("/namespaces").json()["namespaces"]
    assert ns == {"PUBLIC": 1, "RESTRICTED": 1, "TRADE_SECRET": 1}


def test_internal_search_returns_sensitive():
    client.post("/index", json={"text": "환자 차트 기록 혈압", "metadata": _meta("c2", "RESTRICTED")})
    r = client.post("/search", json={"query": "차트 혈압", "project_id": "proj-A", "external": False})
    body = r.json()
    assert len(body["hits"]) == 1
    assert body["export_blocked_count"] == 0


def test_external_search_blocks_sensitive():
    """의료/제조 compliance: RESTRICTED/TRADE_SECRET 외부 LLM 반출 차단."""
    client.post("/index", json={"text": "환자 차트 혈압", "metadata": _meta("c2", "RESTRICTED")})
    client.post("/index", json={"text": "촉매 배합 혈압", "metadata": _meta("c3", "TRADE_SECRET")})
    client.post("/index", json={"text": "공개 혈압 안내", "metadata": _meta("c1", "PUBLIC")})
    r = client.post("/search", json={"query": "혈압", "project_id": "proj-A", "external": True})
    body = r.json()
    assert all(h["sensitivity_level"] == "PUBLIC" for h in body["hits"])
    assert body["export_blocked_count"] == 2


def test_tenant_isolation_no_cross_leak():
    """ict-saas compliance: 크로스테넌트 누출 0."""
    client.post("/index", json={"text": "기밀 혈압 데이터", "metadata": _meta("a1", "INTERNAL", project="proj-A")})
    client.post("/index", json={"text": "기밀 혈압 데이터", "metadata": _meta("b1", "INTERNAL", project="proj-B")})
    r = client.post("/search", json={"query": "기밀 혈압", "project_id": "proj-A", "external": False})
    hits = r.json()["hits"]
    assert len(hits) == 1
    assert hits[0]["chunk_id"] == "a1"


def test_idempotent_upsert():
    store = InMemoryVectorStore()
    from app.index.store import IndexedChunk
    from app.index.schema import ChunkMetadata
    m = ChunkMetadata(**_meta("dup", "PUBLIC"))
    store.upsert(IndexedChunk(metadata=m, text="v1"))
    store.upsert(IndexedChunk(metadata=m, text="v2"))
    assert store.namespaces() == {"PUBLIC": 1}


def test_export_blocked_flag():
    assert SensitivityLevel.RESTRICTED in (SensitivityLevel.RESTRICTED, SensitivityLevel.TRADE_SECRET)
    r = client.post("/index", json={"text": "x", "metadata": _meta("c9", "TRADE_SECRET")})
    assert r.json()["export_blocked"] is True


def test_metrics_llm_sensitive_block(monkeypatch):
    """Epic 6: external 검색의 차단 건수가 llm_sensitive_block_total 로 누적."""
    client.post("/index", json={"text": "환자 혈압", "metadata": _meta("c2", "RESTRICTED")})
    client.post("/search", json={"query": "혈압", "project_id": "proj-A", "external": True})
    m = client.get("/metrics").json()
    assert m["llm_sensitive_block_total"] >= 1
    assert m["chunks_indexed_total"] >= 1
