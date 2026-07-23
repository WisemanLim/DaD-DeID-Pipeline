# test/impl/1 — deid 코어 (Epic 0/1/2) 시나리오

대상: 룰번들 로더 + 검출(regex+Luhn) + 정책엔진 + 변환기 + `POST /deid`.
러너: `cd services/deid && uv run pytest`.

## 시나리오

| # | Given | When | Then (수용 기준) |
|---|---|---|---|
| S1 | Luhn 함수 | 유효/무효 카드번호 | valid Visa True, 변조 False |
| S2 | 주민번호 포함 텍스트 (의료) | `/deid` | 산출물에 RRN 없음, action=REMOVE, **RESTRICTED+export_blocked** (직접식별자 0) |
| S3 | 유효 카드 PAN (금융) | `/deid` | Luhn 통과→TOKENIZE, 원문 미잔존, `⟨TOK:⟩`, vault≥1, export 차단 |
| S4 | Luhn 실패 16자리 | `/deid` | card_pan 오탐 없음 |
| S5 | 전화+이메일 | `/deid` | 둘 다 MASK, 원문 미잔존 |
| S6 | ip(영업비밀) 검출 (제조) | policy+transform | RANGE_BUCKET, **TRADE_SECRET**, 절대값(17.3) 미보존, `⟨RANGE:⟩` |
| S7 | 베이스라인 로더 | seed 없이 baseline() | 내장 privacy 카드룰 존재 |
| S8 | `/rules?industry_code=manufacturing-chemical` | GET | total>0, classifier=unsupported 보고 |

## 도메인 compliance 매핑 (COMPLIANCE.md)
- 의료(Q): S2 — 비식별 검증(재식별 불가)
- 금융(K): S3 — PAN Luhn→토큰화, 외부반출 차단
- 제조(C): S6 — 영업비밀 절대값 미보존, recipe token/RANGE_BUCKET
