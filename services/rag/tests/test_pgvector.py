"""pgvector 어댑터 시험 (impl/10) — DB 가용 시 통합, 미가용 시 skip."""
import os

import pytest

from app.index.pgvector_store import hash_embedding


def test_hash_embedding_deterministic():
    a = hash_embedding("환자 차트 혈압")
    b = hash_embedding("환자 차트 혈압")
    assert a == b
    assert len(a) == 64
    assert abs(sum(v * v for v in a) - 1.0) < 1e-6     # L2 정규화


def _pg_available(dsn) -> bool:
    try:
        import psycopg
        psycopg.connect(dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


DSN = os.getenv("TEST_DATABASE_URL", "postgresql://redactflow:devpass@localhost:5432/redactflow")


@pytest.mark.skipif(not _pg_available(DSN), reason="postgres 미가용(make up 필요)")
def test_pgvector_namespace_and_gate():
    from app.index.pgvector_store import PgVectorStore
    from app.index.schema import ChunkMetadata
    from app.index.store import IndexedChunk

    store = PgVectorStore(DSN)
    store._conn.execute("DELETE FROM rag_chunks WHERE project_id='pgtest'")

    def meta(cid, lvl):
        return ChunkMetadata(
            document_id="d", chunk_id=cid, industry_code="Q", sensitivity_level=lvl,
            transform_action="MASK", lineage={}, source_uri="s", domain="healthcare-clinical",
            project_id="pgtest", owner="u", version="1",
        )

    store.upsert(IndexedChunk(metadata=meta("p1", "PUBLIC"), text="공개 혈압 안내"))
    store.upsert(IndexedChunk(metadata=meta("p2", "RESTRICTED"), text="환자 차트 혈압"))
    # 외부반출 게이트 — RESTRICTED 차단
    hits, blocked = store.query("혈압", "pgtest", external=True)
    assert blocked >= 1
    assert all(h.sensitivity_level.value == "PUBLIC" for h in hits)
    store._conn.execute("DELETE FROM rag_chunks WHERE project_id='pgtest'")
