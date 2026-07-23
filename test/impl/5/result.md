# test/impl/5 — 결과 / result

- 실행일: 2026-06-09
- 판정: **PASS** (deid 19/19 · ruff clean)

```
19 passed   (기존 15 + NER/dict 4)
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_dictionary_detects_trade_secret | PASS |
| S2 | test_ner_detects_korean_person | PASS (NER_PS '김철수') |
| S3 | test_composite_merges_regex_ner_dict | PASS (PRIV_ID + NER_PS + DICT_*) |
| S4 | test_composite_overlap_no_double_count | PASS |

## 구현
- `app/detect/ner.py` — spaCy lazy-load(ko_core_news_sm / en_core_web_sm), 엔티티 라벨(PS/PERSON·LC/GPE·OG/ORG)→pii 서브카테고리
- `app/detect/dictionary.py` — 내장 도메인 렉시콘(영업비밀 용어→ip) + seed dictionary 룰 흡수
- `app/detect/composite.py` — regex+NER+dictionary 병합 + 겹침 해소
- pipeline·/deid 가 CompositeDetector 사용 (config.enable_ner/enable_dict 토글)
- spaCy 모델 2종 pyproject URL 핀 + `allow-direct-references`

## 수정 이력
- **FAIL→PASS**: composite 테스트가 synthetic 로더(seed 없음) 사용 → global RRN 룰 미적재로 regex 미검출.
  실 seed 로더(`settings.seed_dir`)로 변경 후 통과.
- **빌드 오류→수정**: hatchling 이 spaCy 모델 URL 직접참조 거부 → `[tool.hatch.metadata] allow-direct-references=true` 추가.

## 한계 / 잔여
- NER severity=medium 고정(→INTERNAL). 도메인별 가중·신뢰도 임계 후속.
- seed 의 `classifier` 룰(분류기)은 여전히 미지원 — NER/dictionary 로 일부 대체, 전용 분류기 후속.
