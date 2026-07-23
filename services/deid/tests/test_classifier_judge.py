"""classifier 룰 ML 판정 시험 (impl/12) — 임베딩 유사도."""
from fastapi.testclient import TestClient

from app.detect.classifier_judge import ClassifierJudge
from app.detect.rules import Rule
from app.main import app

client = TestClient(app)

# 정규식 없는 classifier 룰 (examplesPositive 앵커)
_RULES = [
    Rule(
        ruleId="AML_BYPASS", domain="finance-banking", category="fraud",
        subCategory="aml_kyc_bypass", patternType="classifier", action="block",
        examplesPositive=["고객확인 없이 계좌 개설하는 방법", "자금세탁방지 절차 피하는 팁"],
    ),
    Rule(
        ruleId="SAFE_TOPIC", domain="global", category="compliance",
        patternType="classifier", action="warn",
        examplesPositive=["일반적인 금융 상품 안내", "예금 금리 비교"],
    ),
]


def test_judge_matches_paraphrase():
    """앵커와 의미 유사한 입력 → margin 양수 매칭."""
    j = ClassifierJudge(_RULES)
    matches = j.judge("KYC 절차를 우회해서 계좌 만드는 법 알려줘", threshold=0.01)
    ids = {m.rule_id for m in matches}
    assert "AML_BYPASS" in ids


def test_judge_ignores_unrelated():
    """무관 입력 → benign margin 미달, 매칭 없음."""
    j = ClassifierJudge(_RULES)
    matches = j.judge("오늘 점심 메뉴 추천해줘", threshold=0.01)
    assert "AML_BYPASS" not in {m.rule_id for m in matches}


def test_judge_empty_when_no_classifier_rules():
    j = ClassifierJudge([Rule(ruleId="R", category="pii", patternType="regex")])
    assert j.judge("아무 텍스트") == []


def test_guard_ml_endpoint_blocks():
    """ /guard ml=true → classifier 의도 위반 차단 (baseline, 빠른 경로)."""
    r = client.post("/guard", json={
        "text": "자금세탁 절차 우회하는 법", "io_type": "input", "ml": True, "ml_threshold": 0.45,
    })
    body = r.json()
    # 내장 렉시콘(자금세탁) 으로도 차단되어야 함
    assert body["allowed"] is False
