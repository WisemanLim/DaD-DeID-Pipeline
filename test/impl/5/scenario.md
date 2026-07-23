# test/impl/5 — NER + dictionary 검출 (Epic 1 완성) 시나리오

대상: `app/detect/{ner,dictionary,composite}.py` — spaCy NER + 용어사전 + regex 병합.
러너: `cd services/deid && uv run pytest`.

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | "촉매비율 17.3%, 배합비율" | DictionaryDetector | ip 카테고리, catalyst_ratio_secret·formulation_secret 검출 |
| S2 | "김철수 환자가 서울에서" | NerDetector(kr) | pii 검출 ≥1, person_name/location/organization |
| S3 | RRN+인명+영업비밀 혼합문 | CompositeDetector | PRIV_ID(regex)+NER_*+DICT_* 동시 검출 |
| S4 | 단일 RRN | CompositeDetector | 검출 스팬 겹침 0 (해소) |

## 도메인 compliance 매핑
- 제조(C): S1 — 영업비밀 용어사전 → RANGE_BUCKET 경로
- 의료(Q)/공통: S2 — 비정형 인명/지명 NER 검출(regex 미포착 보강)
