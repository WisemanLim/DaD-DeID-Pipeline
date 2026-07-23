"""LLM judge 시험 (impl/15) — 키 없으면 no-op(available=False)."""
from app.detect.llm_judge import judge
from app.detect.rules import Rule

_RULE = Rule(
    ruleId="AML", domain="finance-banking", category="fraud", subCategory="aml_kyc_bypass",
    patternType="classifier", action="block",
    examplesPositive=["자금세탁방지 절차 우회"], description="AML 우회",
)


def test_llm_judge_noop_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    v = judge("자금세탁 우회 방법", _RULE)
    assert v.available is False
    assert v.violates is False


def test_guard_llm_flag_graceful(monkeypatch):
    """/guard llm=true 라도 키 없으면 ML 결과 유지(폴백, 예외 없음)."""
    from fastapi.testclient import TestClient

    from app.main import app
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = TestClient(app)
    r = client.post("/guard", json={
        "text": "자금세탁 절차 우회하는 법", "io_type": "input", "ml": True, "llm": True,
        "ml_threshold": 0.45,
    })
    # 내장 렉시콘(자금세탁)으로 차단 유지
    assert r.json()["allowed"] is False
