# test/impl/7 — 도메인 오버레이 검증 (Epic 5) 시나리오

대상: 실 `privacy` seed(46 regex) 적재 + DomainRegistry(KSIC 섹션→서브도메인) + 5도메인 검증.
러너: `cd services/deid && uv run pytest tests/test_domains.py`.

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | seed 디렉터리 | domains_by_section | C/K/Q/O/R 섹션, 서브도메인 매핑 |
| S2 | 카드번호 (베이스라인) | detect | privacy seed regex+Luhn → TOKENIZE |
| S3 | industry_code='C' | load | 제조 전 서브도메인 병합(룰 수 > 단일) |
| S4 | 의료(Q) 진료기록 RRN | detect+policy | REMOVE, RESTRICTED |
| S5 | 제조(C) 촉매비율/반응압력 | detect+policy | RANGE_BUCKET, TRADE_SECRET |
| S6 | 공공(O)·예술(R) 주민번호 | detect+policy | REMOVE (베이스라인 PII) |
| S7 | `/domains` | GET | 섹션 목록 + KSIC 라벨 |

## 도메인 compliance 매핑 (5도메인, PRD Epic 5 순서)
- 제조(C)/의료(Q)/금융(K): 영업비밀·PHI·카드 deid
- 공공(O)/예술(R): 베이스라인 PII (시드 classifier 룰은 NER/dict 보강)
- 비고: 도메인 번들 대부분 `classifier` patternType → regex 검출은 baseline(global+privacy) 중심, 도메인 특화는 NER/dictionary + 후속 분류기
