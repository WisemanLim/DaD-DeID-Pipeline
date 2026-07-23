# test/impl/9 — 결과 / result

- 실행일: 2026-06-10
- 판정: **PASS** (guardrail 6/6 · ruff clean)

```
6 passed
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_block_money_laundering | PASS (BLOCK) |
| S2 | test_refuse_kyc_bypass | PASS (REFUSE/BLOCK) |
| S3 | test_allow_benign | PASS (ALLOW) |
| S4 | test_decision_precedence | PASS |
| S5 | test_guard_endpoint | PASS |
| S6 | test_guard_endpoint_allow | PASS |

## 구현
- `app/guardrail.py` — `GuardrailEngine`: ioType(input/output/both) 필터 + 가드 카테고리(safety/compliance/fraud) regex 룰 + 내장 가드레일 렉시콘. Decision IntEnum 우선순위(BLOCK>REFUSE>REDACT>ADD_DISCLAIMER>WARN>ALLOW)
- deid `POST /guard` — {text, io_type, industry_code} → {decision, allowed, matches, messages}, guard_eval_total/guard_blocked_total 메트릭

## 수정 이력
- 없음.

## 한계 / 잔여
- seed classifier 룰의 ML 분류 판정은 미구현 — regex 룰 + 내장 렉시콘 매칭만. 전용 분류기(임베딩/LLM judge) 후속.
- output 가드(LLM 응답 검사) 동일 엔진 재사용 — 응답 파이프라인 결선은 후속.
