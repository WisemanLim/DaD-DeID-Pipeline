"""NER + dictionary 검출 시험 (Epic 1 완성)."""
from app.core.config import settings
from app.detect.composite import CompositeDetector
from app.detect.dictionary import DictionaryDetector
from app.detect.ner import NerDetector
from app.detect.rules import RuleBundleLoader


def test_dictionary_detects_trade_secret():
    """제조 compliance: 영업비밀 용어 → ip 카테고리(→ RANGE_BUCKET)."""
    dets = DictionaryDetector().detect("촉매비율 17.3%, 배합비율 관리")
    cats = {d.category for d in dets}
    subs = {d.sub_category for d in dets}
    assert "ip" in cats
    assert "catalyst_ratio_secret" in subs
    assert "formulation_secret" in subs


def test_ner_detects_korean_person():
    """spaCy NER — 인명/지명 등 비정형 식별자 검출."""
    dets = NerDetector("kr").detect("김철수 환자가 서울에서 진료받았다.")
    assert len(dets) >= 1
    assert all(d.category == "pii" for d in dets)
    assert {d.sub_category for d in dets} & {"person_name", "location", "organization"}


def test_composite_merges_regex_ner_dict():
    """복합: RRN(regex) + 인명(NER) + 영업비밀(dict) 동시 검출, 겹침 해소."""
    loader = RuleBundleLoader(settings.seed_dir, "kr")     # 실 seed (global RRN 포함)
    rules = loader.load("manufacturing-chemical")
    det = CompositeDetector(rules, "kr", enable_ner=True, enable_dict=True)
    dets = det.detect("김철수 주민번호 900101-1234567, 촉매비율 17.3%")
    rule_ids = {d.rule_id for d in dets}
    assert any(r.startswith("PRIV_ID") for r in rule_ids)       # regex RRN
    assert any(r.startswith("DICT_") for r in rule_ids)         # dictionary 영업비밀
    assert any(r.startswith("NER_") for r in rule_ids)          # NER 인명


def test_composite_overlap_no_double_count():
    """동일 위치 중복 검출은 1건으로 해소(위치 비겹침)."""
    loader = RuleBundleLoader(settings.seed_dir, "kr")
    det = CompositeDetector(loader.load(), "kr")
    dets = det.detect("주민번호 900101-1234567")
    spans = [(d.start, d.end) for d in dets]
    # 겹치는 스팬 없음
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            assert spans[i][1] <= spans[j][0] or spans[j][1] <= spans[i][0]
