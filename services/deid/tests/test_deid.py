"""deid 파이프라인 시험 — 검출/정책/변환 + 도메인 compliance 케이스."""
from fastapi.testclient import TestClient

from app.detect.detector import luhn_valid
from app.detect.rules import RuleBundleLoader
from app.detect.detector import Detection
from app.main import app
from app.policy.engine import DeidAction, PolicyEngine, Sensitivity
from app.transform.transformer import Transformer

client = TestClient(app)


def test_luhn():
    assert luhn_valid("4242424242424242")        # valid test Visa
    assert not luhn_valid("4242424242424241")


def test_rrn_removed_no_direct_identifier():
    """의료 compliance: 산출물에 직접식별자(주민번호) 없음 = 재식별 불가."""
    r = client.post("/deid", json={"text": "환자 주민등록번호는 900101-1234567 입니다."})
    assert r.status_code == 200
    body = r.json()
    assert "900101-1234567" not in body["transformed_text"]
    assert any(d["action"] == "REMOVE" for d in body["detections"])
    assert body["sensitivity_level"] == "RESTRICTED"      # RRN=critical
    assert body["export_blocked"] is True


def test_card_pan_tokenized():
    """금융 compliance: PAN Luhn 검증 후 토큰화, 원문 미잔존, 외부반출 차단."""
    r = client.post("/deid", json={"text": "카드번호 4242 4242 4242 4242 결제"})
    body = r.json()
    assert "4242 4242 4242 4242" not in body["transformed_text"]
    assert any(d["action"] == "TOKENIZE" for d in body["detections"])
    assert "⟨TOK:" in body["transformed_text"]
    assert body["export_blocked"] is True
    assert body["stats"]["vault_entries"] >= 1


def test_invalid_card_not_detected():
    """Luhn 실패 숫자열은 카드로 오탐하지 않음."""
    r = client.post("/deid", json={"text": "주문번호 1234567890123456 처리"})
    cats = [d["category"] for d in r.json()["detections"]]
    assert "financial" not in cats or all(
        d["sub_category"] != "card_pan" for d in r.json()["detections"]
    )


def test_email_phone_masked():
    r = client.post("/deid", json={"text": "연락처 010-1234-5678 메일 hong@test.com"})
    body = r.json()
    assert "hong@test.com" not in body["transformed_text"]
    assert "010-1234-5678" not in body["transformed_text"]
    assert all(d["action"] == "MASK" for d in body["detections"])


def test_ip_trade_secret_range_bucket():
    """제조 compliance: 영업비밀 절대값 미보존, RANGE_BUCKET/recipe token만 잔존."""
    det = Detection(
        rule_id="X", category="ip", sub_category="catalyst_ratio_secret",
        action="block_or_redact", severity="critical", start=0, end=5,
        text="17.3", regulation_tags=["TRADE_SECRET"],
    )
    eng = PolicyEngine()
    dec = eng.decide(det)
    assert dec.action == DeidAction.RANGE_BUCKET
    assert dec.sensitivity == Sensitivity.TRADE_SECRET
    out = Transformer().transform("촉매비율 17.3%", [eng.decide(Detection(
        rule_id="X", category="ip", sub_category="catalyst_ratio_secret",
        action="block_or_redact", severity="critical", start=5, end=9,
        text="17.3", regulation_tags=[],
    ))])
    assert "17.3" not in out
    assert "⟨RANGE:" in out


def test_loader_baseline_has_privacy_card_rule():
    loader = RuleBundleLoader.__new__(RuleBundleLoader)
    loader.seed_dir = __import__("pathlib").Path("/nonexistent")
    loader.locale = "kr"
    loader._cache = {}
    rules = loader.baseline()                       # global(빈) + privacy(내장)
    assert any(r.ruleId == "PRIV_FIN_CARD_001" for r in rules)


def test_rules_endpoint_reports_unsupported():
    r = client.get("/rules", params={"industry_code": "manufacturing-chemical"})
    body = r.json()
    assert body["total"] > 0
    # seed 제조 룰 다수가 classifier → unsupported 보고
    assert "classifier" in body["unsupported_pattern_types"]
