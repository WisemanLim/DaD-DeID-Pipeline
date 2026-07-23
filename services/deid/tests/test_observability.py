"""관측 시험 (Epic 6) — Langfuse 호환 trace + KPI 메트릭."""
from fastapi.testclient import TestClient

from app.main import app
from app.observability import MetricsRegistry, TraceRecorder

client = TestClient(app)


def test_metrics_registry_transform_rate():
    m = MetricsRegistry()
    m.inc("entities_detected_total", 4)
    m.inc("entities_transformed_total", 4)
    snap = m.snapshot()
    assert snap["transform_rate_avg"] == 1.0
    assert MetricsRegistry().snapshot()["transform_rate_avg"] == 0.0  # 0 division guard


def test_trace_recorder_spans():
    rec = TraceRecorder(tags={"industry_code": "Q"})
    with rec.span("deid.detect") as m:
        m["entities_detected"] = 2
    t = rec.trace()
    assert t.tags["industry_code"] == "Q"
    assert t.spans[0].name == "deid.detect"
    assert t.spans[0].metadata["entities_detected"] == 2
    assert t.spans[0].duration_ms >= 0


def test_process_returns_trace_with_prd_tags():
    """PRD §7: trace 상단 = industry·document·policy 메타, span = deid.detect/transform."""
    r = client.post("/process", json={
        "text": "환자 900101-1234567 진료", "document_id": "d1",
        "industry_code": "healthcare-clinical", "project_id": "p",
    })
    trace = r.json()["trace"]
    assert trace["tags"]["industry_code"] == "healthcare-clinical"
    assert trace["tags"]["document_id"] == "d1"
    span_names = {s["name"] for s in trace["spans"]}
    assert {"deid.detect", "deid.transform"} <= span_names


def test_metrics_endpoint_accumulates():
    before = client.get("/metrics").json().get("documents_processed_total", 0)
    client.post("/process", json={"text": "전화 010-1234-5678", "document_id": "d2", "project_id": "p"})
    after = client.get("/metrics").json()
    assert after["documents_processed_total"] == before + 1
    assert after["entities_detected_total"] >= 1
    assert "transform_rate_avg" in after
