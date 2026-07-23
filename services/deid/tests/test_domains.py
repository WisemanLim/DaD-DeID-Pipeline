"""도메인 오버레이 검증 (Epic 5) — 제조/의료/금융/공공/예술 + privacy seed."""
from fastapi.testclient import TestClient

from app.core.config import settings
from app.detect.composite import CompositeDetector
from app.detect.rules import RuleBundleLoader
from app.main import app
from app.policy.engine import DeidAction, PolicyEngine, Sensitivity

client = TestClient(app)
_loader = RuleBundleLoader(settings.seed_dir, "kr")
_policy = PolicyEngine()


def _detect(industry_code, text):
    det = CompositeDetector(_loader.load(industry_code), "kr")
    return [_policy.decide(d) for d in det.detect(text)]


def test_domains_by_section_registry():
    by = _loader.domains_by_section()
    assert set(by) >= {"C", "K", "Q", "O", "R"}
    assert "manufacturing-chemical" in by["C"]
    assert "healthcare-clinical" in by["Q"]
    assert "arts-recreation" in by["R"]


def test_privacy_seed_loaded_card_luhn():
    """실 privacy seed(46 regex) 적재 — 카드 Luhn 검출."""
    decs = _detect(None, "카드 4242 4242 4242 4242")
    assert any(p.action == DeidAction.TOKENIZE for p in decs)


def test_section_load_merges_subdomains():
    """industry_code='C' → 제조 전 서브도메인 병합 (단일 서브도메인보다 룰 많음)."""
    one = len(_loader.load("manufacturing-chemical"))
    section = len(_loader.load("C"))
    assert section > one


def test_healthcare_rrn_removed():
    """의료(Q): 진료기록 RRN → REMOVE, RESTRICTED."""
    decs = _detect("healthcare-clinical", "진료기록 환자 900101-1234567")
    assert any(p.action == DeidAction.REMOVE for p in decs)
    assert _policy.overall_sensitivity(decs) == Sensitivity.RESTRICTED


def test_manufacturing_trade_secret():
    """제조(C): 영업비밀 용어 → RANGE_BUCKET, TRADE_SECRET."""
    decs = _detect("manufacturing-chemical", "촉매비율 17.3% 반응압력 4.2bar")
    assert any(p.action == DeidAction.RANGE_BUCKET for p in decs)
    assert _policy.overall_sensitivity(decs) == Sensitivity.TRADE_SECRET


def test_public_arts_baseline_pii():
    """공공(O)/예술(R): 베이스라인 PII(주민번호) 동작."""
    for code in ("public-administration", "arts-recreation"):
        decs = _detect(code, "민원인 900101-1234567")
        assert any(p.action == DeidAction.REMOVE for p in decs), code


def test_domains_endpoint():
    body = client.get("/domains").json()
    assert "C" in body["sections"]
    assert body["ksic_map"]["Q"] == "의료"
