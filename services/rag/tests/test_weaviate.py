"""Weaviate 어댑터 시험 (impl/15) — 서버 가용 시 통합, 미가용 시 skip."""
import os

import pytest


def _weaviate_available(url) -> bool:
    try:
        import urllib.request
        urllib.request.urlopen(f"{url}/v1/.well-known/ready", timeout=2)
        return True
    except Exception:
        return False


URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")


def test_uuid_deterministic():
    from app.index.weaviate_store import _uuid
    assert _uuid("c1") == _uuid("c1")
    assert len(_uuid("c1")) == 36       # UUID 형식


def test_backend_switch_falls_back(monkeypatch):
    """WEAVIATE 미가용 시 in-memory 폴백(예외 없이 store 생성)."""
    monkeypatch.setenv("VECTOR_BACKEND", "weaviate")
    monkeypatch.setenv("WEAVIATE_URL", "http://127.0.0.1:59998")
    import importlib

    import app.main as m
    importlib.reload(m)
    assert m._store is not None        # 폴백으로 InMemoryVectorStore


@pytest.mark.skipif(not _weaviate_available(URL), reason="weaviate 미가용(--profile vector 필요)")
def test_weaviate_external_gate():
    from app.index.schema import ChunkMetadata
    from app.index.store import IndexedChunk
    from app.index.weaviate_store import WeaviateStore

    s = WeaviateStore(URL)

    def meta(cid, lvl):
        return ChunkMetadata(
            document_id="d", chunk_id=cid, industry_code="Q", sensitivity_level=lvl,
            transform_action="MASK", lineage={}, source_uri="s", domain="healthcare-clinical",
            project_id="wvtest", owner="u", version="1",
        )

    s.upsert(IndexedChunk(metadata=meta("w1", "PUBLIC"), text="공개 혈압 안내"))
    s.upsert(IndexedChunk(metadata=meta("w2", "RESTRICTED"), text="환자 차트 혈압"))
    hits, blocked = s.query("혈압", "wvtest", external=True)
    assert blocked >= 1
    assert all(h.sensitivity_level.value == "PUBLIC" for h in hits)
