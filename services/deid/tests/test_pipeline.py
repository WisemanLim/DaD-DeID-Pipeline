"""파이프라인 시험 — 청킹 + 청크별 비식별 → ChunkMetadata 계약."""
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import chunk_text

client = TestClient(app)


def test_chunker_splits_paragraphs():
    assert chunk_text("문단1\n\n문단2") == ["문단1", "문단2"]
    assert chunk_text("  ") == []


def test_process_emits_chunk_metadata():
    doc = "공개 안내문입니다.\n\n환자 주민번호 900101-1234567 진료기록."
    r = client.post("/process", json={
        "text": doc, "document_id": "docA", "industry_code": "healthcare-clinical",
        "project_id": "proj-A", "owner": "u1",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["chunk_count"] == 2
    # 문서 민감도 = 청크 최대 (RRN 포함 청크 = RESTRICTED)
    assert body["doc_sensitivity_level"] == "RESTRICTED"
    c0, c1 = body["chunks"]
    # 공개 청크 = 검출 없음
    assert c0["metadata"]["sensitivity_level"] == "PUBLIC"
    assert c0["metadata"]["transform_action"] == "NONE"
    # 민감 청크 = RRN 제거됨, lineage 에 rule_id
    assert "900101-1234567" not in c1["text"]
    assert c1["metadata"]["sensitivity_level"] == "RESTRICTED"
    assert "REMOVE" in c1["metadata"]["transform_action"]
    assert c1["metadata"]["lineage"]["rule_ids"]
    assert c1["metadata"]["chunk_id"] == "docA#1"


def test_process_metadata_matches_rag_contract():
    """deid /process 의 metadata 키가 rag ChunkMetadata 필수 필드를 포함(계약 호환)."""
    r = client.post("/process", json={"text": "x", "document_id": "d", "project_id": "p"})
    meta = r.json()["chunks"][0]["metadata"]
    required = {
        "document_id", "chunk_id", "industry_code", "sensitivity_level",
        "transform_action", "lineage", "source_uri", "domain", "project_id",
        "owner", "version",
    }
    assert required <= set(meta)
