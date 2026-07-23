# test/impl/1 — 결과 / result

- 실행일: 2026-06-09
- 러너: `cd services/deid && uv run pytest -q`
- 판정: **PASS (8/8)**

```
8 passed, 1 warning in 0.12s
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_luhn | PASS |
| S2 | test_rrn_removed_no_direct_identifier | PASS (의료: 직접식별자 0) |
| S3 | test_card_pan_tokenized | PASS (금융: PAN 토큰화·차단) |
| S4 | test_invalid_card_not_detected | PASS |
| S5 | test_email_phone_masked | PASS |
| S6 | test_ip_trade_secret_range_bucket | PASS (제조: 절대값 미보존) |
| S7 | test_loader_baseline_has_privacy_card_rule | PASS |
| S8 | test_rules_endpoint_reports_unsupported | PASS |

## 수정 이력 (fix & retest)
- **FAIL→PASS**: `Transformer.__init__` 의 `vault or TokenVault()` — 빈 vault(`__len__`==0)가 falsy 라
  주입 vault 무시 → 새 vault 생성 → `vault_entries=0`. `vault if vault is not None else ...` 로 수정 후 재시험 통과.

## E2E (실서비스 curl)
```
POST /deid {"text":"환자 900101-1234567, 카드 4242 4242 4242 4242, 메일 a@b.com","industry_code":"healthcare-clinical"}
→ transformed: "환자 [REMOVED], 카드 ⟨TOK:9219e0affa⟩, 메일 *@*.***"
  sensitivity=RESTRICTED, export_blocked=true, vault_entries=1
GET /rules?industry_code=manufacturing-chemical
→ total=213, detectable_regex=13, unsupported=[classifier]
```

## 한계 / 잔여
- 검출 = regex + Luhn 만. seed 룰 다수가 `classifier`(NER/분류기) → 이번 슬라이스 미지원(`/rules` unsupported 보고).
- 다음: NER(spaCy/Presidio) 검출기, OCR 경로(Epic 3), 분리 인덱싱(Epic 4), Langfuse trace(Epic 6).
